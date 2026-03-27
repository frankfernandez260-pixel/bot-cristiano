import json
import os
import random
from telebot import types
from database.connection import get_session
from database.models import Usuario, PreguntaVista, Ranking
from services.roles import get_or_create_user

# ── Constantes ────────────────────────────────────────────────────────────────

JUEGO_ID = "millonario"

# Mapeo nivel (1-15) → dificultad del JSON
NIVEL_A_DIFICULTAD = {
    1: "facil", 2: "facil", 3: "facil", 4: "facil",
    5: "media", 6: "media", 7: "media", 8: "media",
    9: "dificil", 10: "dificil", 11: "dificil", 12: "dificil",
    13: "muy_dificil", 14: "muy_dificil", 15: "muy_dificil",
}

# Niveles donde se renuevan los comodines (salvavidas)
SALVAVIDAS_NIVELES = {5, 10, 13}

# Premios por nivel (puntos)
PREMIOS = {
    1: 100, 2: 200, 3: 300, 4: 500,
    5: 1000, 6: 2000, 7: 4000, 8: 8000,
    9: 16000, 10: 32000, 11: 64000, 12: 125000,
    13: 250000, 14: 500000, 15: 1000000,
}

# Puntos garantizados al superar estos niveles
GARANTIZADOS = {5: 1000, 10: 32000}

# Directorio de JSONs — sube un nivel desde games/ hasta la raíz, luego baja a utils/
PREGUNTAS_DIR = os.path.join(os.path.dirname(__file__), "..", "utils", "preguntas", "millonario")

# ── Estado de partidas activas en memoria ─────────────────────────────────────
# { telegram_id: {
#     nivel, grupo_id, grupo_nombre, pregunta_actual,
#     comodines, eliminadas, puntaje_garantizado, preguntas_sesion
# } }
partidas_activas = {}


# ── Helpers de carga de JSONs ─────────────────────────────────────────────────

def obtener_grupos_disponibles() -> list[dict]:
    """Lista los grupos disponibles leyendo los JSONs en disco."""
    grupos = []
    if not os.path.isdir(PREGUNTAS_DIR):
        return grupos
    for archivo in sorted(os.listdir(PREGUNTAS_DIR)):
        if archivo.endswith(".json"):
            ruta = os.path.join(PREGUNTAS_DIR, archivo)
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                grupos.append({
                    "grupo_id": data["grupo_id"],
                    "grupo_nombre": data["grupo_nombre"],
                    "archivo": archivo,
                    "total": data.get("total_preguntas", len(data["preguntas"])),
                })
            except Exception:
                pass
    return grupos


def cargar_preguntas_grupo(grupo_id: str) -> list[dict]:
    """Carga las preguntas de un grupo específico."""
    if not os.path.isdir(PREGUNTAS_DIR):
        return []
    for archivo in os.listdir(PREGUNTAS_DIR):
        if archivo.endswith(".json"):
            ruta = os.path.join(PREGUNTAS_DIR, archivo)
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data["grupo_id"] == grupo_id:
                    return data["preguntas"]
            except Exception:
                pass
    return []


def cargar_preguntas_general() -> list[dict]:
    """Mezcla preguntas de todos los grupos."""
    todas = []
    if not os.path.isdir(PREGUNTAS_DIR):
        return todas
    for archivo in os.listdir(PREGUNTAS_DIR):
        if archivo.endswith(".json"):
            ruta = os.path.join(PREGUNTAS_DIR, archivo)
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                todas.extend(data["preguntas"])
            except Exception:
                pass
    return todas


# ── Selección de pregunta ─────────────────────────────────────────────────────

def obtener_pregunta(telegram_id: int, nivel: int, grupo_id: str) -> dict | None:
    """
    Selecciona una pregunta no vista para este usuario en este nivel.
    - Excluye preguntas ya vistas en sesiones anteriores (BD).
    - Excluye preguntas ya vistas en esta sesión (memoria).
    - Si se agotan ambos pools, resetea y vuelve a empezar.
    """
    dificultad = NIVEL_A_DIFICULTAD[nivel]

    if grupo_id == "GENERAL":
        pool_json = cargar_preguntas_general()
    else:
        pool_json = cargar_preguntas_grupo(grupo_id)

    pool = [p for p in pool_json if p["dificultad"] == dificultad]

    if not pool:
        return None

    # IDs ya usados en esta sesión activa
    sesion_ids = partidas_activas.get(telegram_id, {}).get("preguntas_sesion", set())

    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(telegram_id=telegram_id).first()
        if not usuario:
            # Sin usuario en BD: solo excluir sesión
            disponibles = [p for p in pool if p["id"] not in sesion_ids]
            if not disponibles:
                disponibles = pool
            pregunta = random.choice(disponibles)
            sesion_ids.add(pregunta["id"])
            return pregunta

        # IDs ya vistos en BD para este juego+grupo+nivel
        vistos = session.query(PreguntaVista).filter_by(
            user_id=usuario.id,
            juego=f"{JUEGO_ID}_{grupo_id}_{nivel}",
        ).all()
        ids_vistos = {v.pregunta_id for v in vistos}

        # Excluir vistas en BD Y en sesión actual
        no_vistos = [
            p for p in pool
            if p["id"] not in ids_vistos and p["id"] not in sesion_ids
        ]

        # Si se agotó el pool: resetear BD y sesión
        if not no_vistos:
            for v in vistos:
                session.delete(v)
            session.commit()
            if telegram_id in partidas_activas:
                partidas_activas[telegram_id]["preguntas_sesion"] = set()
                sesion_ids = set()
            no_vistos = pool

        pregunta = random.choice(no_vistos)

        # Marcar como vista en BD
        nueva_vista = PreguntaVista(
            user_id=usuario.id,
            pregunta_id=pregunta["id"],
            juego=f"{JUEGO_ID}_{grupo_id}_{nivel}",
        )
        session.add(nueva_vista)
        session.commit()

        # Marcar como vista en sesión
        if telegram_id in partidas_activas:
            partidas_activas[telegram_id]["preguntas_sesion"].add(pregunta["id"])

        return pregunta
    finally:
        session.close()


# ── Teclados ──────────────────────────────────────────────────────────────────

def teclado_respuestas(opciones: dict, eliminadas: set = None) -> types.ReplyKeyboardMarkup:
    eliminadas = eliminadas or set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    botones = []
    for letra in ["A", "B", "C", "D"]:
        if letra not in eliminadas:
            botones.append(types.KeyboardButton(f"{letra}) {opciones[letra]}"))
        else:
            botones.append(types.KeyboardButton("❌ Eliminada"))
    markup.add(*botones)
    markup.add(types.KeyboardButton("🚪 Abandonar"))
    return markup


def teclado_comodines(comodines: dict) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=3)
    botones = []
    if comodines.get("cincuenta"):
        botones.append(types.InlineKeyboardButton("50/50 🎲", callback_data="mm_comodin_cincuenta"))
    if comodines.get("saltar"):
        botones.append(types.InlineKeyboardButton("Saltar ⏭️", callback_data="mm_comodin_saltar"))
    if comodines.get("estadistica"):
        botones.append(types.InlineKeyboardButton("Estadística 📊", callback_data="mm_comodin_estadistica"))
    if botones:
        markup.add(*botones)
    return markup


def teclado_seleccion_grupo(grupos: list[dict]) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for g in grupos:
        markup.add(types.KeyboardButton(f"📖 {g['grupo_nombre']} ({g['total']} preguntas)"))
    markup.add(types.KeyboardButton("🌍 Biblia General (todos los grupos)"))
    markup.add(types.KeyboardButton("❌ Cancelar"))
    return markup


# ── Formateo de pregunta ──────────────────────────────────────────────────────

def formatear_pregunta(pregunta: dict, nivel: int, eliminadas: set = None) -> str:
    """
    Encabezado con Markdown. Texto de pregunta y opciones sin Markdown
    para evitar errores con caracteres especiales (*, _, (, ), etc.).
    """
    eliminadas = eliminadas or set()
    premio = PREMIOS[nivel]
    prev_garantizado = max((v for k, v in GARANTIZADOS.items() if k < nivel), default=0)

    encabezado = (
        f"✝️ *Millonario Bíblico*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Nivel *{nivel}/15* — 💰 {premio:,} pts\n"
        f"🛡️ Garantizados: {prev_garantizado:,} pts\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    cuerpo = f"❓ {pregunta['pregunta']}\n\n"
    for letra in ["A", "B", "C", "D"]:
        if letra in eliminadas:
            cuerpo += f"{letra}) ——\n"
        else:
            cuerpo += f"{letra}) {pregunta['opciones'][letra]}\n"

    return encabezado + cuerpo


# ── Registro principal ────────────────────────────────────────────────────────

def register(bot):

    # ── Entrada: botón del menú de juegos ─────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🏆 Millonario Bíblico")
    def iniciar_millonario(message):
        get_or_create_user(message.from_user)

        grupos = obtener_grupos_disponibles()
        if not grupos:
            bot.send_message(
                message.chat.id,
                "⚠️ Aún no hay preguntas cargadas. "
                "Pídele al administrador que cargue los JSONs.",
            )
            return

        bot.send_message(
            message.chat.id,
            "✝️ *Millonario Bíblico*\n\nElige con qué grupo quieres jugar:",
            parse_mode="Markdown",
            reply_markup=teclado_seleccion_grupo(grupos),
        )
        bot.register_next_step_handler(message, recibir_seleccion_grupo, grupos)

    # ── Selección de grupo ────────────────────────────────────────────────────
    def recibir_seleccion_grupo(message, grupos):
        tid = message.from_user.id

        if message.text == "❌ Cancelar":
            _volver_menu_juegos(bot, message)
            return

        grupo_id = None
        grupo_nombre = None

        if message.text.startswith("🌍"):
            grupo_id = "GENERAL"
            grupo_nombre = "Biblia General"
        else:
            for g in grupos:
                if g["grupo_nombre"] in message.text:
                    grupo_id = g["grupo_id"]
                    grupo_nombre = g["grupo_nombre"]
                    break

        if not grupo_id:
            bot.send_message(message.chat.id, "❌ Opción no válida. Intenta de nuevo.")
            bot.register_next_step_handler(message, recibir_seleccion_grupo, grupos)
            return

        # Inicializar estado de la partida
        partidas_activas[tid] = {
            "nivel": 1,
            "grupo_id": grupo_id,
            "grupo_nombre": grupo_nombre,
            "comodines": {"cincuenta": True, "saltar": True, "estadistica": True},
            "eliminadas": set(),
            "puntaje_garantizado": 0,
            "pregunta_actual": None,
            "preguntas_sesion": set(),
        }

        bot.send_message(
            message.chat.id,
            f"✅ Modo: *{grupo_nombre}*\n\n"
            "🎮 15 preguntas de dificultad progresiva.\n"
            "🛡️ Comodines renovados en niveles 5, 10 y 13.\n"
            "🎲 Comodines: 50/50, Saltar, Estadística.\n\n"
            "¡Que Dios ilumine tu mente! 🙏",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove(),
        )

        _enviar_pregunta(bot, message, tid)

    # ── Enviar pregunta del nivel actual ──────────────────────────────────────
    def _enviar_pregunta(bot, message, tid):
        estado = partidas_activas.get(tid)
        if not estado:
            return

        nivel = estado["nivel"]

        # Renovar comodines en niveles salvavidas
        if nivel in SALVAVIDAS_NIVELES:
            estado["comodines"] = {"cincuenta": True, "saltar": True, "estadistica": True}
            estado["eliminadas"] = set()
            bot.send_message(
                message.chat.id,
                f"🛡️ *¡Salvavidas! Nivel {nivel}*\nTus comodines han sido renovados.",
                parse_mode="Markdown",
            )

        pregunta = obtener_pregunta(tid, nivel, estado["grupo_id"])
        if not pregunta:
            bot.send_message(
                message.chat.id,
                "⚠️ No hay preguntas disponibles para este nivel.",
                reply_markup=_menu_juegos_markup(),
            )
            partidas_activas.pop(tid, None)
            return

        estado["pregunta_actual"] = pregunta
        estado["eliminadas"] = set()

        # Enviar comodines disponibles como inline
        if any(estado["comodines"].values()):
            bot.send_message(
                message.chat.id,
                "🎲 *Comodines disponibles:*",
                parse_mode="Markdown",
                reply_markup=teclado_comodines(estado["comodines"]),
            )

        bot.send_message(
            message.chat.id,
            formatear_pregunta(pregunta, nivel),
            parse_mode="Markdown",
            reply_markup=teclado_respuestas(pregunta["opciones"]),
        )
        bot.register_next_step_handler(message, recibir_respuesta)

    # ── Botones del menú principal — guard contra handler huérfano ───────────
    _BOTONES_MENU = {
        "🏛️ Iglesias", "⭐ Mis Iglesias", "📚 Biblioteca", "🎵 Música",
        "📅 Eventos", "📰 Noticias", "📖 Testimonios", "🤝 Consejería",
        "💬 Debates", "🙏 Oración", "🎮 Juega y Aprende", "📿 Versículo del Día",
        "🔙 Menú Principal",
    }

    # ── Recibir respuesta del usuario ─────────────────────────────────────────
    def recibir_respuesta(message):
        tid = message.from_user.id
        estado = partidas_activas.get(tid)

        if not estado:
            return

        # Si el usuario pulsó un botón del menú principal, cancelar la partida
        # sin bloquear el handler de ese botón.
        if message.text in _BOTONES_MENU:
            partidas_activas.pop(tid, None)
            bot.send_message(message.chat.id, "⚠️ Partida cancelada al salir del juego.")
            return  # El listener del menú tomará el relevo

        if message.text == "🚪 Abandonar":
            _terminar_partida(bot, message, tid, abandono=True)
            return

        texto = (message.text or "").strip()
        if not texto or texto[0] not in ("A", "B", "C", "D"):
            bot.send_message(message.chat.id, "❓ Responde eligiendo A, B, C o D.")
            bot.register_next_step_handler(message, recibir_respuesta)
            return

        letra_elegida = texto[0]

        # Verificar que la opción no esté eliminada por 50/50
        if letra_elegida in estado["eliminadas"]:
            bot.send_message(message.chat.id, "❌ Esa opción fue eliminada. Elige otra.")
            bot.register_next_step_handler(message, recibir_respuesta)
            return

        pregunta = estado["pregunta_actual"]
        correcta = pregunta["correcta"]
        nivel = estado["nivel"]

        if letra_elegida == correcta:
            if nivel in GARANTIZADOS:
                estado["puntaje_garantizado"] = GARANTIZADOS[nivel]

            bot.send_message(
                message.chat.id,
                f"✅ *¡Correcto!*\n\n"
                f"💡 _{pregunta['explicacion']}_\n\n"
                f"💰 Ganaste *{PREMIOS[nivel]:,}* puntos.",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove(),
            )

            if nivel == 15:
                _terminar_partida(bot, message, tid, ganador=True)
            else:
                estado["nivel"] += 1
                _enviar_pregunta(bot, message, tid)
        else:
            bot.send_message(
                message.chat.id,
                f"❌ *¡Incorrecto!*\n\n"
                f"La correcta era: *{correcta})* {pregunta['opciones'][correcta]}\n\n"
                f"💡 _{pregunta['explicacion']}_",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove(),
            )
            _terminar_partida(bot, message, tid, ganador=False)

    # ── Comodines (callbacks inline) ──────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("mm_comodin_"))
    def manejar_comodin(call):
        tid = call.from_user.id
        estado = partidas_activas.get(tid)

        if not estado:
            bot.answer_callback_query(call.id, "No hay partida activa.")
            return

        comodin = call.data.replace("mm_comodin_", "")
        pregunta = estado["pregunta_actual"]

        if not pregunta:
            bot.answer_callback_query(call.id, "Espera a que aparezca la pregunta.")
            return

        # ── 50/50 ──────────────────────────────────────────────────────────
        if comodin == "cincuenta":
            if not estado["comodines"]["cincuenta"]:
                bot.answer_callback_query(call.id, "Ya usaste este comodín.")
                return
            estado["comodines"]["cincuenta"] = False

            incorrectas = [
                l for l in ["A", "B", "C", "D"]
                if l != pregunta["correcta"] and l not in estado["eliminadas"]
            ]
            eliminar = random.sample(incorrectas, min(2, len(incorrectas)))
            estado["eliminadas"].update(eliminar)

            bot.answer_callback_query(call.id, "50/50 aplicado ✂️")
            bot.send_message(
                call.message.chat.id,
                formatear_pregunta(pregunta, estado["nivel"], estado["eliminadas"]),
                parse_mode="Markdown",
                reply_markup=teclado_respuestas(pregunta["opciones"], estado["eliminadas"]),
            )

        # ── Saltar ─────────────────────────────────────────────────────────
        elif comodin == "saltar":
            if not estado["comodines"]["saltar"]:
                bot.answer_callback_query(call.id, "Ya usaste este comodín.")
                return
            estado["comodines"]["saltar"] = False

            # Añadir la pregunta actual a sesión para no repetirla
            estado["preguntas_sesion"].add(pregunta["id"])

            bot.answer_callback_query(call.id, "Pregunta cambiada ⏭️")

            # Cargar nueva pregunta directamente (sin llamar _enviar_pregunta
            # para no crear un next_step_handler nuevo desde call.message)
            nueva = obtener_pregunta(tid, estado["nivel"], estado["grupo_id"])
            if not nueva:
                bot.send_message(call.message.chat.id, "⚠️ No hay más preguntas disponibles.")
                return

            estado["pregunta_actual"] = nueva
            estado["eliminadas"] = set()

            if any(estado["comodines"].values()):
                bot.send_message(
                    call.message.chat.id,
                    "🎲 *Comodines disponibles:*",
                    parse_mode="Markdown",
                    reply_markup=teclado_comodines(estado["comodines"]),
                )

            bot.send_message(
                call.message.chat.id,
                formatear_pregunta(nueva, estado["nivel"]),
                parse_mode="Markdown",
                reply_markup=teclado_respuestas(nueva["opciones"]),
            )
            # El next_step_handler de recibir_respuesta sigue activo — correcto.

        # ── Estadística ────────────────────────────────────────────────────
        elif comodin == "estadistica":
            if not estado["comodines"]["estadistica"]:
                bot.answer_callback_query(call.id, "Ya usaste este comodín.")
                return
            estado["comodines"]["estadistica"] = False

            correcta = pregunta["correcta"]
            letras = [l for l in ["A", "B", "C", "D"] if l not in estado["eliminadas"]]
            pesos = {l: random.randint(5, 20) for l in letras}
            pesos[correcta] = random.randint(40, 65)
            total = sum(pesos.values())
            stats = "\n".join(
                f"*{l})* {'█' * (pesos[l] * 10 // total)} {pesos[l] * 100 // total}%"
                for l in letras
            )

            bot.answer_callback_query(call.id, "Estadística mostrada 📊")
            bot.send_message(
                call.message.chat.id,
                f"📊 *¿Cómo respondieron otros jugadores?*\n\n{stats}",
                parse_mode="Markdown",
            )

    # ── Fin de partida ────────────────────────────────────────────────────────
    def _terminar_partida(bot, message, tid, ganador=False, abandono=False):
        estado = partidas_activas.pop(tid, {})
        nivel_alcanzado = estado.get("nivel", 1)
        grupo_nombre = estado.get("grupo_nombre", "")

        if ganador:
            puntaje_final = PREMIOS[15]
            nivel_guardado = 15
            texto_final = (
                "🏆 *¡FELICITACIONES!*\n\n"
                "✝️ ¡Completaste los 15 niveles!\n"
                "💰 Puntaje final: *1,000,000 puntos*\n\n"
                "\"Porque Jehová da la sabiduría, y de su boca viene\n"
                "el conocimiento y la inteligencia.\"\n— Proverbios 2:6"
            )
        elif abandono:
            puntaje_final = estado.get("puntaje_garantizado", 0)
            nivel_guardado = nivel_alcanzado - 1 if nivel_alcanzado > 1 else 0
            texto_final = (
                f"🚪 *Partida abandonada*\n\n"
                f"📊 Llegaste al nivel *{nivel_alcanzado}*\n"
                f"💰 Puntos garantizados: *{puntaje_final:,}*"
            )
        else:
            # Perdió: nivel completado = nivel en que falló - 1
            puntaje_final = estado.get("puntaje_garantizado", 0)
            nivel_guardado = nivel_alcanzado - 1 if nivel_alcanzado > 1 else 0
            texto_final = (
                f"💔 *Juego terminado*\n\n"
                f"📊 Fallaste en el nivel *{nivel_alcanzado}*\n"
                f"✅ Último nivel completado: *{nivel_guardado}*\n"
                f"💰 Puntos garantizados: *{puntaje_final:,}*\n\n"
                "\"Confía en Jehová con todo tu corazón.\"\n— Proverbios 3:5"
            )

        _guardar_ranking(tid, puntaje_final, nivel_guardado, grupo_nombre)

        bot.send_message(
            message.chat.id,
            texto_final,
            parse_mode="Markdown",
            reply_markup=_menu_juegos_markup(),
        )

    # ── Guardar en ranking ────────────────────────────────────────────────────
    def _guardar_ranking(tid, puntaje, nivel, grupo):
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(telegram_id=tid).first()
            if not usuario:
                return

            existente = session.query(Ranking).filter_by(
                user_id=usuario.id,
                juego=f"{JUEGO_ID}_{grupo}",
            ).first()

            if existente:
                if puntaje > existente.puntaje:
                    existente.puntaje = puntaje
                    existente.nivel_max = nivel
                    session.commit()
            else:
                session.add(Ranking(
                    user_id=usuario.id,
                    juego=f"{JUEGO_ID}_{grupo}",
                    puntaje=puntaje,
                    nivel_max=nivel,
                ))
                session.commit()
        finally:
            session.close()

    # ── Teclados de navegación ────────────────────────────────────────────────
    def _menu_juegos_markup():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🏆 Millonario Bíblico"),
            types.KeyboardButton("🔙 Menú Principal"),
        )
        return markup

    def _volver_menu_juegos(bot, message):
        from handlers.start import menu_principal
        bot.send_message(
            message.chat.id,
            "🎮 Juegos",
            reply_markup=menu_principal(message.from_user.id),
        )

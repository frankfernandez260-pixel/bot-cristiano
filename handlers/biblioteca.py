from telebot import types
from database.connection import get_session
from database.models import ArchivosBiblioteca, Usuario
from services.roles import get_or_create_user, tiene_rol, es_admin
from utils.constants import TIPOS_BIBLIOTECA

# ── Cache ─────────────────────────────────────────────────────────────────────
busqueda_cache = {}

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📚 Biblioteca")
    def seccion_biblioteca(message):
        get_or_create_user(message.from_user)
        es_ed = tiene_rol(message.from_user.id, "editor_biblioteca") or es_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "📚 *Biblioteca*\n\n¿Qué quieres explorar?",
            parse_mode="Markdown",
            reply_markup=kb_menu_biblioteca(es_ed)
        )

    # ── Biblia ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📖 Biblia")
    def seccion_biblia(message):
        session = get_session()
        try:
            biblias = session.query(ArchivosBiblioteca).filter_by(tipo="biblia").all()
            if not biblias:
                bot.send_message(
                    message.chat.id,
                    "😔 No hay biblias disponibles aún.",
                    reply_markup=kb_menu_biblioteca(es_admin(message.from_user.id))
                )
                return

            markup = types.InlineKeyboardMarkup(row_width=2)
            for b in biblias:
                markup.add(types.InlineKeyboardButton(
                    b.version or b.titulo,
                    callback_data=f"biblioteca_enviar_{b.id}"
                ))

            bot.send_message(
                message.chat.id,
                "📖 *Biblias disponibles*\n\nSelecciona la versión:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        finally:
            session.close()

    # ── Literatura ────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📗 Literatura")
    def seccion_literatura(message):
        es_ed = tiene_rol(message.from_user.id, "editor_biblioteca") or es_admin(message.from_user.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🔍 Buscar por Título"),
            types.KeyboardButton("👤 Buscar por Autor"),
        )
        markup.add(types.KeyboardButton("📋 Ver Catálogo"))
        if es_ed:
            markup.add(types.KeyboardButton("➕ Agregar Libro"))
        markup.add(types.KeyboardButton("🔙 Biblioteca"))
        bot.send_message(
            message.chat.id,
            "📗 *Literatura Cristiana*",
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda m: m.text == "🔍 Buscar por Título")
    def buscar_titulo(message):
        bot.send_message(
            message.chat.id,
            "Escribe el título o parte de él:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, paso_buscar_titulo)

    def paso_buscar_titulo(message):
        if message.text == "🔙 Biblioteca":
            seccion_biblioteca(message)
            return
        es_ed = tiene_rol(message.from_user.id, "editor_biblioteca") or es_admin(message.from_user.id)
        session = get_session()
        try:
            resultados = session.query(ArchivosBiblioteca).filter(
                ArchivosBiblioteca.tipo == "literatura",
                ArchivosBiblioteca.titulo.ilike(f"%{message.text}%")
            ).all()
            _mostrar_resultados_biblioteca(bot, message.chat.id, resultados, es_ed)
        finally:
            session.close()

    @bot.message_handler(func=lambda m: m.text == "👤 Buscar por Autor")
    def buscar_autor(message):
        bot.send_message(
            message.chat.id,
            "Escribe el nombre del autor:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, paso_buscar_autor)

    def paso_buscar_autor(message):
        if message.text == "🔙 Biblioteca":
            seccion_biblioteca(message)
            return
        es_ed = tiene_rol(message.from_user.id, "editor_biblioteca") or es_admin(message.from_user.id)
        session = get_session()
        try:
            resultados = session.query(ArchivosBiblioteca).filter(
                ArchivosBiblioteca.tipo == "literatura",
                ArchivosBiblioteca.autor.ilike(f"%{message.text}%")
            ).all()
            _mostrar_resultados_biblioteca(bot, message.chat.id, resultados, es_ed)
        finally:
            session.close()

    @bot.message_handler(func=lambda m: m.text == "📋 Ver Catálogo")
    def ver_catalogo(message):
        session = get_session()
        try:
            libros = session.query(ArchivosBiblioteca).filter(
                ArchivosBiblioteca.tipo.in_(["literatura", "catecismo", "devocional"])
            ).order_by(ArchivosBiblioteca.tipo, ArchivosBiblioteca.titulo).all()

            if not libros:
                bot.send_message(message.chat.id, "😔 No hay libros disponibles aún.")
                return

            lineas = ["📋 *Catálogo disponible*\n"]
            tipo_actual = None
            for libro in libros:
                if libro.tipo != tipo_actual:
                    tipo_actual = libro.tipo
                    emoji = {"literatura": "📗", "catecismo": "📜", "devocional": "🎙️"}.get(tipo_actual, "📄")
                    lineas.append(f"\n{emoji} *{tipo_actual.capitalize()}*")
                autor = f" — {libro.autor}" if libro.autor else ""
                lineas.append(f"• {libro.titulo}{autor}")

            bot.send_message(
                message.chat.id,
                "\n".join(lineas),
                parse_mode="Markdown"
            )
        finally:
            session.close()

    # ── Catecismo ─────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📜 Catecismo")
    def seccion_catecismo(message):
        session = get_session()
        try:
            catecismos = session.query(ArchivosBiblioteca).filter_by(tipo="catecismo").all()
            if not catecismos:
                bot.send_message(message.chat.id, "😔 No hay catecismos disponibles aún.")
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for c in catecismos:
                markup.add(types.InlineKeyboardButton(
                    c.titulo,
                    callback_data=f"biblioteca_enviar_{c.id}"
                ))

            bot.send_message(
                message.chat.id,
                "📜 *Catecismo*\n\nSelecciona:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        finally:
            session.close()

    # ── Devocionales ──────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🎙️ Devocionales")
    def seccion_devocionales(message):
        session = get_session()
        try:
            devocionales = session.query(ArchivosBiblioteca).filter_by(tipo="devocional").all()
            if not devocionales:
                bot.send_message(message.chat.id, "😔 No hay devocionales disponibles aún.")
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for d in devocionales:
                markup.add(types.InlineKeyboardButton(
                    d.titulo,
                    callback_data=f"biblioteca_enviar_{d.id}"
                ))

            bot.send_message(
                message.chat.id,
                "🎙️ *Devocionales*\n\nSelecciona:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        finally:
            session.close()

    # ── Enviar archivo ────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("biblioteca_enviar_"))
    def enviar_archivo(call):
        archivo_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            archivo = session.query(ArchivosBiblioteca).filter_by(id=archivo_id).first()
            if not archivo:
                bot.answer_callback_query(call.id, "Archivo no encontrado.")
                return

            bot.answer_callback_query(call.id, "📤 Enviando...")
            caption = f"📄 *{archivo.titulo}*"
            if archivo.autor:
                caption += f"\n✍️ {archivo.autor}"
            if archivo.version:
                caption += f"\n📖 Versión: {archivo.version}"

            bot.send_document(
                call.message.chat.id,
                archivo.file_id,
                caption=caption,
                parse_mode="Markdown"
            )
        finally:
            session.close()

    # ── Agregar archivo (editores) ────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "➕ Agregar Libro")
    def agregar_libro(message):
        if not tiene_rol(message.from_user.id, "editor_biblioteca") and not es_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ No tienes permiso.")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("📖 Biblia"),
            types.KeyboardButton("📗 Literatura"),
            types.KeyboardButton("📜 Catecismo"),
            types.KeyboardButton("🎙️ Devocional"),
        )
        markup.add(types.KeyboardButton("❌ Cancelar"))
        bot.send_message(
            message.chat.id,
            "¿Qué tipo de archivo vas a agregar?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_tipo_archivo)

    def reg_tipo_archivo(message):
        if message.text == "❌ Cancelar":
            seccion_biblioteca(message)
            return

        tipos_map = {
            "📖 Biblia": "biblia",
            "📗 Literatura": "literatura",
            "📜 Catecismo": "catecismo",
            "🎙️ Devocional": "devocional",
        }

        if message.text not in tipos_map:
            bot.send_message(message.chat.id, "Selecciona una opción válida.")
            bot.register_next_step_handler(message, reg_tipo_archivo)
            return

        busqueda_cache[message.from_user.id] = {"tipo": tipos_map[message.text]}
        bot.send_message(
            message.chat.id,
            "¿Cuál es el título?",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, reg_titulo_archivo)

    def reg_titulo_archivo(message):
        if message.text == "❌ Cancelar":
            seccion_biblioteca(message)
            return

        busqueda_cache[message.from_user.id]["titulo"] = message.text
        tipo = busqueda_cache[message.from_user.id].get("tipo")

        if tipo == "biblia":
            bot.send_message(message.chat.id, "¿Cuál es la versión? (ej: RVR60, NVI, LBLA)")
            bot.register_next_step_handler(message, reg_version_archivo)
        else:
            bot.send_message(message.chat.id, "¿Quién es el autor? (o escribe *Omitir*)", parse_mode="Markdown")
            bot.register_next_step_handler(message, reg_autor_archivo)

    def reg_version_archivo(message):
        busqueda_cache[message.from_user.id]["version"] = message.text
        busqueda_cache[message.from_user.id]["autor"] = None
        bot.send_message(message.chat.id, "Ahora reenvía o sube el archivo de la Biblia:")
        bot.register_next_step_handler(message, reg_file_archivo)

    def reg_autor_archivo(message):
        if message.text.lower() == "omitir":
            busqueda_cache[message.from_user.id]["autor"] = None
        else:
            busqueda_cache[message.from_user.id]["autor"] = message.text

        bot.send_message(message.chat.id, "Ahora reenvía o sube el archivo:")
        bot.register_next_step_handler(message, reg_file_archivo)

    def reg_file_archivo(message):
        if not message.document:
            bot.send_message(message.chat.id, "Por favor envía o reenvía el archivo como documento.")
            bot.register_next_step_handler(message, reg_file_archivo)
            return

        cache = busqueda_cache.get(message.from_user.id, {})
        file_id = message.document.file_id

        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()

            nuevo = ArchivosBiblioteca(
                tipo=cache.get("tipo"),
                titulo=cache.get("titulo"),
                autor=cache.get("autor"),
                version=cache.get("version"),
                file_id=file_id,
                subido_por=usuario.id if usuario else None,
            )
            session.add(nuevo)
            session.commit()

            busqueda_cache.pop(message.from_user.id, None)
            es_ed = tiene_rol(message.from_user.id, "editor_biblioteca") or es_admin(message.from_user.id)
            bot.send_message(
                message.chat.id,
                f"✅ *{cache.get('titulo')}* agregado a la biblioteca.",
                parse_mode="Markdown",
                reply_markup=kb_menu_biblioteca(es_ed)
            )
        finally:
            session.close()

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Biblioteca")
    def volver_biblioteca(message):
        seccion_biblioteca(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_biblioteca(es_editor: bool = False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📖 Biblia"),
        types.KeyboardButton("📗 Literatura"),
        types.KeyboardButton("📜 Catecismo"),
        types.KeyboardButton("🎙️ Devocionales"),
    )
    if es_editor:
        markup.add(types.KeyboardButton("➕ Agregar Libro"))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup


def _mostrar_resultados_biblioteca(bot, chat_id, resultados, es_editor=False):
    if not resultados:
        bot.send_message(
            chat_id,
            "😔 No encontré resultados.",
            reply_markup=kb_menu_biblioteca(es_editor)
        )
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in resultados:
        autor = f" — {r.autor}" if r.autor else ""
        markup.add(types.InlineKeyboardButton(
            f"{r.titulo}{autor}",
            callback_data=f"biblioteca_enviar_{r.id}"
        ))

    bot.send_message(
        chat_id,
        f"📚 Encontré *{len(resultados)}* resultado(s):",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.send_message(chat_id, "👇", reply_markup=kb_menu_biblioteca(es_editor))
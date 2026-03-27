from telebot import types
from database.connection import get_session
from database.models import Cancion, Usuario
from services.roles import get_or_create_user, tiene_rol, es_admin
from utils.constants import GENEROS_MUSICA

# ── Cache ─────────────────────────────────────────────────────────────────────
busqueda_cache = {}

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🎵 Música")
    def seccion_musica(message):
        get_or_create_user(message.from_user)
        es_ed = tiene_rol(message.from_user.id, "editor_musica") or es_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "🎵 *Música y Alabanza*\n\n¿Qué quieres hacer?",
            parse_mode="Markdown",
            reply_markup=kb_menu_musica(es_ed)
        )

    # ── Buscar por género ─────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🎼 Buscar por Género")
    def buscar_genero(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for g in GENEROS_MUSICA:
            markup.add(types.KeyboardButton(g))
        markup.add(types.KeyboardButton("🔙 Música"))
        bot.send_message(
            message.chat.id,
            "¿Qué género quieres escuchar?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_genero)

    def paso_genero(message):
        if message.text == "🔙 Música":
            seccion_musica(message)
            return

        if message.text not in GENEROS_MUSICA:
            bot.send_message(message.chat.id, "Selecciona un género válido.")
            bot.register_next_step_handler(message, paso_genero)
            return

        es_ed = tiene_rol(message.from_user.id, "editor_musica") or es_admin(message.from_user.id)
        session = get_session()
        try:
            canciones = session.query(Cancion).filter_by(genero=message.text).all()
            _mostrar_lista_canciones(bot, message.chat.id, canciones, es_ed)
        finally:
            session.close()

    # ── Buscar por título ─────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔍 Buscar Canción")
    def buscar_cancion(message):
        bot.send_message(
            message.chat.id,
            "Escribe el título o parte de él:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, paso_buscar_cancion)

    def paso_buscar_cancion(message):
        if message.text == "🔙 Música":
            seccion_musica(message)
            return

        es_ed = tiene_rol(message.from_user.id, "editor_musica") or es_admin(message.from_user.id)
        session = get_session()
        try:
            canciones = session.query(Cancion).filter(
                Cancion.titulo.ilike(f"%{message.text}%")
            ).all()
            _mostrar_lista_canciones(bot, message.chat.id, canciones, es_ed)
        finally:
            session.close()

    # ── Buscar por artista ────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "👤 Buscar por Artista")
    def buscar_artista(message):
        bot.send_message(
            message.chat.id,
            "Escribe el nombre del artista:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, paso_buscar_artista)

    def paso_buscar_artista(message):
        if message.text == "🔙 Música":
            seccion_musica(message)
            return

        es_ed = tiene_rol(message.from_user.id, "editor_musica") or es_admin(message.from_user.id)
        session = get_session()
        try:
            canciones = session.query(Cancion).filter(
                Cancion.artista.ilike(f"%{message.text}%")
            ).all()
            _mostrar_lista_canciones(bot, message.chat.id, canciones, es_ed)
        finally:
            session.close()

    # ── Enviar canción ────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("musica_enviar_"))
    def enviar_cancion(call):
        cancion_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            cancion = session.query(Cancion).filter_by(id=cancion_id).first()
            if not cancion:
                bot.answer_callback_query(call.id, "Canción no encontrada.")
                return

            bot.answer_callback_query(call.id, "🎵 Enviando...")
            caption = f"🎵 *{cancion.titulo}*"
            if cancion.artista:
                caption += f"\n🎤 {cancion.artista}"
            if cancion.genero:
                caption += f"\n🎼 {cancion.genero}"

            bot.send_audio(
                call.message.chat.id,
                cancion.file_id,
                caption=caption,
                parse_mode="Markdown"
            )
        finally:
            session.close()

    # ── Agregar canción (editores) ────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "➕ Agregar Canción")
    def agregar_cancion(message):
        if not tiene_rol(message.from_user.id, "editor_musica") and not es_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ No tienes permiso.")
            return

        busqueda_cache[message.from_user.id] = {}
        bot.send_message(
            message.chat.id,
            "¿Cuál es el título de la canción?",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, reg_titulo_cancion)

    def reg_titulo_cancion(message):
        if message.text == "❌ Cancelar":
            seccion_musica(message)
            return

        busqueda_cache[message.from_user.id]["titulo"] = message.text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "¿Quién es el artista? O toca *Omitir*.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_artista_cancion)

    def reg_artista_cancion(message):
        if message.text == "❌ Cancelar":
            seccion_musica(message)
            return

        busqueda_cache[message.from_user.id]["artista"] = (
            None if message.text == "⏭️ Omitir" else message.text
        )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for g in GENEROS_MUSICA:
            markup.add(types.KeyboardButton(g))
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "¿Qué género es?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_genero_cancion)

    def reg_genero_cancion(message):
        if message.text == "❌ Cancelar":
            seccion_musica(message)
            return

        busqueda_cache[message.from_user.id]["genero"] = (
            None if message.text == "⏭️ Omitir" else message.text
        )

        bot.send_message(
            message.chat.id,
            "Ahora reenvía o sube el audio:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, reg_audio_cancion)

    def reg_audio_cancion(message):
        if not message.audio and not message.document:
            bot.send_message(message.chat.id, "Por favor envía el archivo de audio.")
            bot.register_next_step_handler(message, reg_audio_cancion)
            return

        file_id = message.audio.file_id if message.audio else message.document.file_id
        cache = busqueda_cache.get(message.from_user.id, {})

        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()

            nueva = Cancion(
                titulo=cache.get("titulo"),
                artista=cache.get("artista"),
                genero=cache.get("genero"),
                file_id=file_id,
                subido_por=usuario.id if usuario else None,
            )
            session.add(nueva)
            session.commit()

            busqueda_cache.pop(message.from_user.id, None)
            es_ed = tiene_rol(message.from_user.id, "editor_musica") or es_admin(message.from_user.id)
            bot.send_message(
                message.chat.id,
                f"✅ *{cache.get('titulo')}* agregada al catálogo.",
                parse_mode="Markdown",
                reply_markup=kb_menu_musica(es_ed)
            )
        finally:
            session.close()

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Música")
    def volver_musica(message):
        seccion_musica(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_musica(es_editor: bool = False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🎼 Buscar por Género"),
        types.KeyboardButton("🔍 Buscar Canción"),
        types.KeyboardButton("👤 Buscar por Artista"),
    )
    if es_editor:
        markup.add(types.KeyboardButton("➕ Agregar Canción"))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup


def _mostrar_lista_canciones(bot, chat_id, canciones, es_editor=False):
    if not canciones:
        bot.send_message(
            chat_id,
            "😔 No encontré canciones.",
            reply_markup=kb_menu_musica(es_editor)
        )
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for c in canciones:
        artista = f" — {c.artista}" if c.artista else ""
        markup.add(types.InlineKeyboardButton(
            f"🎵 {c.titulo}{artista}",
            callback_data=f"musica_enviar_{c.id}"
        ))

    bot.send_message(
        chat_id,
        f"🎵 Encontré *{len(canciones)}* canción(es):",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.send_message(chat_id, "👇", reply_markup=kb_menu_musica(es_editor))
from telebot import types
from database.connection import get_session
from database.models import Evento, EventoInscrito, Usuario
from services.roles import get_or_create_user, tiene_rol, es_admin
from utils.constants import PROVINCIAS
from datetime import datetime

# ── Cache ─────────────────────────────────────────────────────────────────────
registro_cache = {}

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📅 Eventos")
    def seccion_eventos(message):
        get_or_create_user(message.from_user)
        es_ed = tiene_rol(message.from_user.id, "editor_eventos") or es_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "📅 *Eventos Generales*\n\n¿Qué quieres hacer?",
            parse_mode="Markdown",
            reply_markup=kb_menu_eventos(es_ed)
        )

    # ── Ver todos los eventos ─────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📋 Ver Eventos")
    def ver_eventos(message):
        session = get_session()
        try:
            ahora = datetime.utcnow()
            eventos = session.query(Evento).filter(
                Evento.iglesia_id == None,
                Evento.fecha_evento >= ahora
            ).order_by(Evento.fecha_evento).all()

            if not eventos:
                bot.send_message(
                    message.chat.id,
                    "😔 No hay eventos próximos.",
                    reply_markup=kb_menu_eventos(es_admin(message.from_user.id))
                )
                return

            bot.send_message(
                message.chat.id,
                f"📅 Hay *{len(eventos)}* evento(s) próximo(s).",
                parse_mode="Markdown"
            )
            _mostrar_eventos(bot, message.chat.id, eventos, message.from_user.id)
        finally:
            session.close()

    # ── Buscar por provincia ──────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🗺️ Buscar por Provincia")
    def buscar_por_provincia(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for p in PROVINCIAS:
            markup.add(types.KeyboardButton(p))
        markup.add(types.KeyboardButton("🔙 Eventos"))
        bot.send_message(
            message.chat.id,
            "¿En qué provincia?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_provincia_evento)

    def paso_provincia_evento(message):
        if message.text == "🔙 Eventos":
            seccion_eventos(message)
            return

        if message.text not in PROVINCIAS:
            bot.send_message(message.chat.id, "Selecciona una provincia válida.")
            bot.register_next_step_handler(message, paso_provincia_evento)
            return

        session = get_session()
        try:
            ahora = datetime.utcnow()
            eventos = session.query(Evento).filter(
                Evento.iglesia_id == None,
                Evento.provincia == message.text,
                Evento.fecha_evento >= ahora
            ).order_by(Evento.fecha_evento).all()

            es_ed = tiene_rol(message.from_user.id, "editor_eventos") or es_admin(message.from_user.id)

            if not eventos:
                bot.send_message(
                    message.chat.id,
                    f"😔 No hay eventos próximos en {message.text}.",
                    reply_markup=kb_menu_eventos(es_ed)
                )
                return

            bot.send_message(
                message.chat.id,
                f"📅 *{len(eventos)}* evento(s) en {message.text}.",
                parse_mode="Markdown",
                reply_markup=kb_menu_eventos(es_ed)
            )
            _mostrar_eventos(bot, message.chat.id, eventos, message.from_user.id)
        finally:
            session.close()

    # ── Publicar evento (editores) ────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "➕ Publicar Evento")
    def publicar_evento(message):
        if not tiene_rol(message.from_user.id, "editor_eventos") and not es_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ No tienes permiso.")
            return

        registro_cache[message.from_user.id] = {}
        bot.send_message(
            message.chat.id,
            "📅 *Publicar nuevo evento*\n\n¿Cuál es el título?",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, reg_titulo_evento)

    def reg_titulo_evento(message):
        if message.text == "/cancelar":
            seccion_eventos(message)
            return

        registro_cache[message.from_user.id]["titulo"] = message.text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "¿Tienes una descripción? O toca *Omitir*.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_descripcion_evento)

    def reg_descripcion_evento(message):
        if message.text == "/cancelar":
            seccion_eventos(message)
            return

        registro_cache[message.from_user.id]["descripcion"] = (
            None if message.text == "⏭️ Omitir" else message.text
        )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for p in PROVINCIAS:
            markup.add(types.KeyboardButton(p))
        markup.add(types.KeyboardButton("🌐 Nacional"))
        bot.send_message(
            message.chat.id,
            "¿En qué provincia es el evento?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_provincia_evento)

    def reg_provincia_evento(message):
        if message.text == "/cancelar":
            seccion_eventos(message)
            return

        registro_cache[message.from_user.id]["provincia"] = (
            None if message.text == "🌐 Nacional" else message.text
        )

        bot.send_message(
            message.chat.id,
            "¿Cuándo es el evento?\n\nEscribe la fecha y hora en este formato:\n"
            "*DD/MM/AAAA HH:MM*\n\nEjemplo: 25/12/2025 18:00",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, reg_fecha_evento)

    def reg_fecha_evento(message):
        if message.text == "/cancelar":
            seccion_eventos(message)
            return

        try:
            fecha = datetime.strptime(message.text.strip(), "%d/%m/%Y %H:%M")
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Formato incorrecto. Usa DD/MM/AAAA HH:MM\nEjemplo: 25/12/2025 18:00"
            )
            bot.register_next_step_handler(message, reg_fecha_evento)
            return

        registro_cache[message.from_user.id]["fecha_evento"] = fecha
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "📸 ¿Tienes un cartel o imagen del evento? O toca *Omitir*.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_imagen_evento)

    def reg_imagen_evento(message):
        if message.text == "/cancelar":
            seccion_eventos(message)
            return

        if message.photo:
            registro_cache[message.from_user.id]["imagen_file_id"] = message.photo[-1].file_id
        else:
            registro_cache[message.from_user.id]["imagen_file_id"] = None

        _mostrar_preview_evento(bot, message)

    def _mostrar_preview_evento(bot, message):
        cache = registro_cache.get(message.from_user.id, {})
        fecha = cache.get("fecha_evento")
        fecha_str = fecha.strftime("%d/%m/%Y %H:%M") if fecha else "Sin fecha"
        provincia = cache.get("provincia") or "Nacional"

        texto = (
            f"📋 *Vista previa*\n\n"
            f"📅 *{cache.get('titulo')}*\n"
            f"🗓️ {fecha_str}\n"
            f"🗺️ {provincia}\n\n"
            f"{cache.get('descripcion') or ''}\n\n"
            f"¿Publicar este evento?"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Publicar", callback_data="evento_confirmar_publicar"),
            types.InlineKeyboardButton("❌ Cancelar", callback_data="evento_confirmar_cancelar"),
        )

        if cache.get("imagen_file_id"):
            bot.send_photo(
                message.chat.id,
                cache["imagen_file_id"],
                caption=texto,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            bot.send_message(
                message.chat.id,
                texto,
                parse_mode="Markdown",
                reply_markup=markup
            )

    @bot.callback_query_handler(func=lambda c: c.data == "evento_confirmar_publicar")
    def confirmar_evento(call):
        cache = registro_cache.get(call.from_user.id, {})
        if not cache:
            bot.answer_callback_query(call.id, "Sesión expirada.")
            return

        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=call.from_user.id
            ).first()

            nuevo = Evento(
                titulo=cache.get("titulo"),
                descripcion=cache.get("descripcion"),
                provincia=cache.get("provincia"),
                fecha_evento=cache.get("fecha_evento"),
                imagen_file_id=cache.get("imagen_file_id"),
                publicado_por=usuario.id if usuario else None,
            )
            session.add(nuevo)
            session.commit()

            registro_cache.pop(call.from_user.id, None)
            bot.answer_callback_query(call.id, "✅ Evento publicado.")
            es_ed = tiene_rol(call.from_user.id, "editor_eventos") or es_admin(call.from_user.id)
            bot.send_message(
                call.message.chat.id,
                "✅ *¡Evento publicado exitosamente!*",
                parse_mode="Markdown",
                reply_markup=kb_menu_eventos(es_ed)
            )
        finally:
            session.close()

    @bot.callback_query_handler(func=lambda c: c.data == "evento_confirmar_cancelar")
    def cancelar_evento(call):
        registro_cache.pop(call.from_user.id, None)
        bot.answer_callback_query(call.id, "❌ Cancelado.")
        es_ed = tiene_rol(call.from_user.id, "editor_eventos") or es_admin(call.from_user.id)
        bot.send_message(
            call.message.chat.id,
            "❌ Publicación cancelada.",
            reply_markup=kb_menu_eventos(es_ed)
        )

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Eventos")
    def volver_eventos(message):
        seccion_eventos(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_eventos(es_editor: bool = False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📋 Ver Eventos"),
        types.KeyboardButton("🗺️ Buscar por Provincia"),
    )
    if es_editor:
        markup.add(types.KeyboardButton("➕ Publicar Evento"))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup


def _mostrar_eventos(bot, chat_id, eventos, user_telegram_id):
    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(
            telegram_id=user_telegram_id
        ).first()

        for ev in eventos:
            fecha = ev.fecha_evento.strftime("%d/%m/%Y %H:%M")
            provincia = ev.provincia or "Nacional"
            inscrito = False
            recordatorio = False

            if usuario:
                from database.models import EventoInscrito
                ins = session.query(EventoInscrito).filter_by(
                    user_id=usuario.id,
                    evento_id=ev.id
                ).first()
                if ins:
                    inscrito = True
                    recordatorio = ins.recordatorio

            texto = (
                f"📅 *{ev.titulo}*\n"
                f"🗓️ {fecha}\n"
                f"🗺️ {provincia}\n\n"
                f"{ev.descripcion or ''}"
            )

            from keyboards.iglesias_kb import kb_evento
            markup = kb_evento(ev.id, inscrito, recordatorio)

            if ev.imagen_file_id:
                bot.send_photo(
                    chat_id,
                    ev.imagen_file_id,
                    caption=texto,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            else:
                bot.send_message(
                    chat_id,
                    texto,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
    finally:
        session.close()
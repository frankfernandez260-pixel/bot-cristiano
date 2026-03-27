from telebot import types
from database.connection import get_session
from database.models import Testimonio, Usuario
from services.roles import get_or_create_user, tiene_rol, es_admin
from utils.constants import CATEGORIAS_TESTIMONIO
from datetime import datetime

# ── Cache ─────────────────────────────────────────────────────────────────────
registro_cache = {}

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📖 Testimonios")
    def seccion_testimonios(message):
        get_or_create_user(message.from_user)
        es_mod = tiene_rol(message.from_user.id, "moderador") or es_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "📖 *Testimonios*\n\nComparte lo que Dios ha hecho en tu vida.",
            parse_mode="Markdown",
            reply_markup=kb_menu_testimonios(es_mod)
        )

    # ── Ver testimonios ───────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "👁️ Ver Testimonios")
    def ver_testimonios(message):
        session = get_session()
        try:
            ahora = datetime.utcnow()
            testimonios = session.query(Testimonio).filter(
                Testimonio.aprobado == True,
                Testimonio.fecha_expiracion > ahora
            ).order_by(Testimonio.fecha_creacion.desc()).all()

            if not testimonios:
                bot.send_message(
                    message.chat.id,
                    "😔 No hay testimonios disponibles aún.",
                    reply_markup=kb_menu_testimonios(
                        tiene_rol(message.from_user.id, "moderador") or es_admin(message.from_user.id)
                    )
                )
                return

            bot.send_message(
                message.chat.id,
                f"📖 Hay *{len(testimonios)}* testimonio(s).",
                parse_mode="Markdown"
            )

            for t in testimonios:
                usuario = session.query(Usuario).filter_by(id=t.user_id).first()
                nombre = "Anónimo 🙏" if t.anonimo else (
                    f"@{usuario.username}" if usuario and usuario.username else
                    usuario.nombre if usuario else "Desconocido"
                )
                categoria = f"🏷️ {t.categoria}\n" if t.categoria else ""
                fecha = t.fecha_creacion.strftime("%d/%m/%Y")

                texto = (
                    f"📖 *Testimonio*\n"
                    f"👤 {nombre} · 📅 {fecha}\n"
                    f"{categoria}\n"
                    f"{t.texto}"
                )

                if t.foto_file_id:
                    bot.send_photo(
                        message.chat.id,
                        t.foto_file_id,
                        caption=texto,
                        parse_mode="Markdown"
                    )
                else:
                    bot.send_message(
                        message.chat.id,
                        texto,
                        parse_mode="Markdown"
                    )

            bot.send_message(
                message.chat.id,
                "📖 Esos son todos los testimonios.",
                reply_markup=kb_menu_testimonios(
                    tiene_rol(message.from_user.id, "moderador") or es_admin(message.from_user.id)
                )
            )
        finally:
            session.close()

    # ── Enviar testimonio ─────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "✍️ Enviar Testimonio")
    def enviar_testimonio(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🙈 Anónimo"),
            types.KeyboardButton("👤 Con mi nombre"),
        )
        markup.add(types.KeyboardButton("❌ Cancelar"))
        bot.send_message(
            message.chat.id,
            "¿Quieres compartir tu testimonio de forma anónima?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_anonimo)

    def paso_anonimo(message):
        if message.text == "❌ Cancelar":
            seccion_testimonios(message)
            return

        if message.text not in ["🙈 Anónimo", "👤 Con mi nombre"]:
            bot.send_message(message.chat.id, "Por favor selecciona una opción.")
            bot.register_next_step_handler(message, paso_anonimo)
            return

        registro_cache[message.from_user.id] = {
            "anonimo": message.text == "🙈 Anónimo"
        }

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cat in CATEGORIAS_TESTIMONIO:
            markup.add(types.KeyboardButton(cat))
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "¿Qué categoría describe mejor tu testimonio?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_categoria)

    def paso_categoria(message):
        if message.text == "❌ Cancelar":
            seccion_testimonios(message)
            return

        registro_cache[message.from_user.id]["categoria"] = (
            None if message.text == "⏭️ Omitir" else message.text
        )

        bot.send_message(
            message.chat.id,
            "✍️ Escribe tu testimonio:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, paso_texto)

    def paso_texto(message):
        if message.text == "❌ Cancelar":
            seccion_testimonios(message)
            return

        if not message.text or len(message.text) < 10:
            bot.send_message(message.chat.id, "Por favor escribe un testimonio más detallado.")
            bot.register_next_step_handler(message, paso_texto)
            return

        registro_cache[message.from_user.id]["texto"] = message.text

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "📸 ¿Quieres agregar una foto? O toca *Omitir*.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_foto)

    def paso_foto(message):
        if message.photo:
            registro_cache[message.from_user.id]["foto_file_id"] = message.photo[-1].file_id
        else:
            registro_cache[message.from_user.id]["foto_file_id"] = None

        cache = registro_cache.get(message.from_user.id, {})
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()

            nuevo = Testimonio(
                user_id=usuario.id,
                anonimo=cache.get("anonimo", False),
                categoria=cache.get("categoria"),
                texto=cache.get("texto"),
                foto_file_id=cache.get("foto_file_id"),
                aprobado=False,
            )
            session.add(nuevo)
            session.commit()
            testimonio_id = nuevo.id

            registro_cache.pop(message.from_user.id, None)
            bot.send_message(
                message.chat.id,
                "✅ Tu testimonio fue enviado y está pendiente de aprobación.\n"
                "¡Gracias por compartir lo que Dios ha hecho en tu vida! 🙏",
                reply_markup=kb_menu_testimonios(False)
            )

            # Notificar a moderadores y admin
            _notificar_moderadores(bot, session, testimonio_id)

        finally:
            session.close()

    # ── Panel de moderación ───────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🛡️ Moderar")
    def moderar_testimonios(message):
        if not tiene_rol(message.from_user.id, "moderador") and not es_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ No tienes permiso.")
            return

        session = get_session()
        try:
            pendientes = session.query(Testimonio).filter_by(aprobado=False).all()

            if not pendientes:
                bot.send_message(
                    message.chat.id,
                    "✅ No hay testimonios pendientes de aprobación.",
                    reply_markup=kb_menu_testimonios(True)
                )
                return

            bot.send_message(
                message.chat.id,
                f"🛡️ *{len(pendientes)}* testimonio(s) pendiente(s):",
                parse_mode="Markdown"
            )

            for t in pendientes:
                usuario = session.query(Usuario).filter_by(id=t.user_id).first()
                nombre = "Anónimo" if t.anonimo else (
                    f"@{usuario.username}" if usuario and usuario.username else
                    usuario.nombre if usuario else "Desconocido"
                )
                categoria = f"🏷️ {t.categoria}\n" if t.categoria else ""

                texto = (
                    f"📖 *Testimonio pendiente #{t.id}*\n"
                    f"👤 {nombre}\n"
                    f"{categoria}\n"
                    f"{t.texto}"
                )

                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("✅ Aprobar", callback_data=f"test_aprobar_{t.id}"),
                    types.InlineKeyboardButton("❌ Rechazar", callback_data=f"test_rechazar_{t.id}"),
                )

                if t.foto_file_id:
                    bot.send_photo(
                        message.chat.id,
                        t.foto_file_id,
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
        finally:
            session.close()

    @bot.callback_query_handler(func=lambda c: c.data.startswith("test_aprobar_"))
    def aprobar_testimonio(call):
        testimonio_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            t = session.query(Testimonio).filter_by(id=testimonio_id).first()
            if not t:
                bot.answer_callback_query(call.id, "Testimonio no encontrado.")
                return
            t.aprobado = True
            session.commit()
            bot.answer_callback_query(call.id, "✅ Testimonio aprobado.")
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )

            # Notificar al usuario
            usuario = session.query(Usuario).filter_by(id=t.user_id).first()
            if usuario:
                try:
                    bot.send_message(
                        usuario.telegram_id,
                        "✅ Tu testimonio fue aprobado y ya está visible para todos. 🙏"
                    )
                except Exception:
                    pass
        finally:
            session.close()

    @bot.callback_query_handler(func=lambda c: c.data.startswith("test_rechazar_"))
    def rechazar_testimonio(call):
        testimonio_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            t = session.query(Testimonio).filter_by(id=testimonio_id).first()
            if not t:
                bot.answer_callback_query(call.id, "Testimonio no encontrado.")
                return
            session.delete(t)
            session.commit()
            bot.answer_callback_query(call.id, "❌ Testimonio rechazado.")
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
        finally:
            session.close()

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Testimonios")
    def volver_testimonios(message):
        seccion_testimonios(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_testimonios(es_moderador: bool = False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("👁️ Ver Testimonios"),
        types.KeyboardButton("✍️ Enviar Testimonio"),
    )
    if es_moderador:
        markup.add(types.KeyboardButton("🛡️ Moderar"))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup


def _notificar_moderadores(bot, session, testimonio_id):
    from database.models import Rol
    moderadores = session.query(Rol).filter(
        Rol.rol.in_(["moderador", "admin"])
    ).all()

    from config.settings import ADMIN_ID
    notificados = {ADMIN_ID}

    try:
        bot.send_message(
            ADMIN_ID,
            f"🛡️ Nuevo testimonio pendiente de aprobación (#{testimonio_id}).\n"
            f"Toca *🛡️ Moderar* en la sección Testimonios.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    for mod in moderadores:
        usuario = session.query(Usuario).filter_by(id=mod.user_id).first()
        if usuario and usuario.telegram_id not in notificados:
            try:
                bot.send_message(
                    usuario.telegram_id,
                    f"🛡️ Nuevo testimonio pendiente de aprobación (#{testimonio_id}).\n"
                    f"Toca *🛡️ Moderar* en la sección Testimonios.",
                    parse_mode="Markdown"
                )
                notificados.add(usuario.telegram_id)
            except Exception:
                pass
from telebot import types
from database.connection import get_session
from database.models import Oracion, Usuario
from services.roles import get_or_create_user
from datetime import datetime

# ── Cache ─────────────────────────────────────────────────────────────────────
registro_cache = {}

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🙏 Oración")
    def seccion_oracion(message):
        get_or_create_user(message.from_user)
        bot.send_message(
            message.chat.id,
            "🙏 *Oración*\n\n"
            "Comparte tus motivos de oración con la comunidad "
            "y ora por los demás. 💙",
            parse_mode="Markdown",
            reply_markup=kb_menu_oracion()
        )

    # ── Enviar motivo ─────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📤 Enviar Motivo")
    def enviar_motivo(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🙈 Anónimo"),
            types.KeyboardButton("👤 Con mi nombre"),
        )
        markup.add(types.KeyboardButton("❌ Cancelar"))
        bot.send_message(
            message.chat.id,
            "¿Quieres enviar tu motivo de forma anónima?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_anonimo)

    def paso_anonimo(message):
        if message.text == "❌ Cancelar":
            seccion_oracion(message)
            return

        if message.text not in ["🙈 Anónimo", "👤 Con mi nombre"]:
            bot.send_message(message.chat.id, "Por favor selecciona una opción.")
            bot.register_next_step_handler(message, paso_anonimo)
            return

        registro_cache[message.from_user.id] = {
            "anonimo": message.text == "🙈 Anónimo"
        }

        bot.send_message(
            message.chat.id,
            "🙏 Escribe tu motivo de oración:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, paso_texto)

    def paso_texto(message):
        if message.text == "❌ Cancelar":
            seccion_oracion(message)
            return

        if not message.text or len(message.text) < 5:
            bot.send_message(message.chat.id, "Por favor escribe algo más detallado.")
            bot.register_next_step_handler(message, paso_texto)
            return

        cache = registro_cache.get(message.from_user.id, {})

        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()

            nueva = Oracion(
                user_id=usuario.id,
                anonimo=cache.get("anonimo", False),
                texto=message.text,
                activa=True,
            )
            session.add(nueva)
            session.commit()

            registro_cache.pop(message.from_user.id, None)
            bot.send_message(
                message.chat.id,
                "✅ Tu motivo fue compartido. "
                "La comunidad orará por ti. 🙏",
                reply_markup=kb_menu_oracion()
            )
        finally:
            session.close()

    # ── Ver motivos ───────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📥 Ver Motivos")
    def ver_motivos(message):
        session = get_session()
        try:
            peticiones = session.query(Oracion).filter_by(
                activa=True
            ).order_by(Oracion.fecha_creacion.desc()).all()

            if not peticiones:
                bot.send_message(
                    message.chat.id,
                    "😔 No hay motivos de oración activos.",
                    reply_markup=kb_menu_oracion()
                )
                return

            bot.send_message(
                message.chat.id,
                f"🙏 Hay *{len(peticiones)}* motivo(s) de oración.\n\n"
                "Ora por cada uno de ellos 💙",
                parse_mode="Markdown"
            )

            for p in peticiones:
                usuario = session.query(Usuario).filter_by(id=p.user_id).first()
                nombre = "Anónimo 🙏" if p.anonimo else (
                    f"@{usuario.username}" if usuario and usuario.username else
                    usuario.nombre if usuario else "Desconocido"
                )
                fecha = p.fecha_creacion.strftime("%d/%m/%Y")

                texto = (
                    f"🙏 *Motivo de oración*\n"
                    f"👤 {nombre} · 📅 {fecha}\n\n"
                    f"{p.texto}"
                )

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    f"🙏 Oré por esto ({p.contador_oro})",
                    callback_data=f"oracion_ore_{p.id}"
                ))

                bot.send_message(
                    message.chat.id,
                    texto,
                    parse_mode="Markdown",
                    reply_markup=markup
                )

            bot.send_message(
                message.chat.id,
                "🙏 Gracias por orar por la comunidad.",
                reply_markup=kb_menu_oracion()
            )
        finally:
            session.close()

    # ── Contador de oración ───────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("oracion_ore_"))
    def ore_por_esto(call):
        oracion_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            oracion = session.query(Oracion).filter_by(id=oracion_id).first()
            if not oracion:
                bot.answer_callback_query(call.id, "Petición no encontrada.")
                return

            oracion.contador_oro += 1
            session.commit()

            bot.answer_callback_query(call.id, "🙏 ¡Gracias por orar!")
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(
                        f"🙏 Oré por esto ({oracion.contador_oro})",
                        callback_data=f"oracion_ore_{oracion_id}"
                    )
                )
            )
        finally:
            session.close()

    # ── Oración del día ───────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📿 Oración del Día")
    def oracion_del_dia(message):
        oraciones = [
            "Señor, gracias por este nuevo día. Guía mis pasos y que todo lo que haga sea para tu gloria. Amén. 🙏",
            "Padre celestial, dame sabiduría para tomar buenas decisiones hoy. Que tu voluntad se haga en mi vida. Amén. 🙏",
            "Dios mío, en tus manos pongo este día. Protégeme, guíame y ayúdame a ser una bendición para quienes me rodean. Amén. 🙏",
            "Señor Jesús, renueva mis fuerzas hoy. Que tu paz que sobrepasa todo entendimiento guarde mi corazón. Amén. 🙏",
            "Padre, gracias por tu amor incondicional. Ayúdame a amarte a ti y a mi prójimo con todo mi corazón. Amén. 🙏",
        ]

        from datetime import date
        indice = date.today().toordinal() % len(oraciones)

        bot.send_message(
            message.chat.id,
            f"📿 *Oración del Día*\n\n_{oraciones[indice]}_",
            parse_mode="Markdown",
            reply_markup=kb_menu_oracion()
        )

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Oración")
    def volver_oracion(message):
        seccion_oracion(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_oracion():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📤 Enviar Motivo"),
        types.KeyboardButton("📥 Ver Motivos"),
        types.KeyboardButton("📿 Oración del Día"),
    )
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup
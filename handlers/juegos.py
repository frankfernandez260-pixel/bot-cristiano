from telebot import types
from services.roles import get_or_create_user
from games import millonario


def register(bot):

    # ── Cancelar cualquier flujo activo ───────────────────────────────────────
    @bot.message_handler(commands=["cancelar"])
    def cmd_cancelar(message):
        bot.clear_step_handler_by_chat_id(message.chat.id)
        partidas_activas.pop(message.from_user.id, None)
        from handlers.start import menu_principal
        bot.send_message(
            message.chat.id,
            "❌ Operación cancelada.",
            reply_markup=menu_principal(message.from_user.id),
        )

    @bot.message_handler(func=lambda m: m.text == "🎮 Juega y Aprende")
    def menu_juegos(message):
        get_or_create_user(message.from_user)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            types.KeyboardButton("🏆 Millonario Bíblico"),
            types.KeyboardButton("🔙 Menú Principal"),
        )

        bot.send_message(
            message.chat.id,
            "🎮 *Juega y Aprende*\n\n"
            "Pon a prueba tu conocimiento bíblico:\n\n"
            "🏆 *Millonario Bíblico* — 15 niveles de dificultad progresiva. "
            "Elige un libro o juega con toda la Biblia.",
            parse_mode="Markdown",
            reply_markup=markup,
        )

    @bot.message_handler(func=lambda m: m.text == "🔙 Menú Principal")
    def volver_menu(message):
        from handlers.start import menu_principal
        bot.send_message(
            message.chat.id,
            "✝️ Menú Principal",
            reply_markup=menu_principal(message.from_user.id),
        )

    # Registrar juegos
    millonario.register(bot)

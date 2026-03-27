from telebot import types
from database.models import init_db
from services.roles import get_or_create_user, es_admin, es_editor

def register(bot):

    @bot.message_handler(commands=["start"])
    def cmd_start(message):
        get_or_create_user(message.from_user)
        nombre = message.from_user.first_name

        texto = (
            f"✝️ ¡Bienvenido, {nombre}!\n\n"
            "Este es tu espacio cristiano en Telegram. "
            "Aquí puedes explorar iglesias, leer la Biblia, "
            "escuchar alabanzas, compartir testimonios y mucho más.\n\n"
            "Usa el menú para navegar 👇"
        )

        bot.send_message(
            message.chat.id,
            texto,
            reply_markup=menu_principal(message.from_user.id)
        )

    @bot.message_handler(func=lambda m: m.text == "📿 Versículo del Día")
    def btn_versiculo(message):
        bot.send_message(message.chat.id, "📿 Versículo del Día — próximamente.")
def menu_principal(telegram_id: int):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    botones = [
        "🏛️ Iglesias",       "⭐ Mis Iglesias",
        "📚 Biblioteca",      "🎵 Música",
        "📅 Eventos",         "📰 Noticias",
        "📖 Testimonios",     "🤝 Consejería",
        "💬 Debates",         "🙏 Oración",
        "🎮 Juega y Aprende", "📿 Versículo del Día",
    ]

    markup.add(*[types.KeyboardButton(b) for b in botones])
    return markup

from telebot import types
from services.roles import get_or_create_user
from utils.constants import CATEGORIAS_CONSEJERIA

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🤝 Consejería")
    def seccion_consejeria(message):
        get_or_create_user(message.from_user)
        bot.send_message(
            message.chat.id,
            "🤝 *Consejería*\n\n"
            "Si estás pasando por un momento difícil, "
            "hay personas dispuestas a escucharte y ayudarte.\n\n"
            "¿En qué área necesitas orientación?",
            parse_mode="Markdown",
            reply_markup=kb_categorias_consejeria()
        )

    # ── Seleccionar categoría ─────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text in CATEGORIAS_CONSEJERIA)
    def seleccionar_categoria(message):
        categoria = message.text
        consejeros = CONSEJEROS.get(categoria, [])

        if not consejeros:
            bot.send_message(
                message.chat.id,
                "😔 No hay consejeros disponibles para esta área en este momento.",
                reply_markup=kb_categorias_consejeria()
            )
            return

        bot.send_message(
            message.chat.id,
            f"🤝 *Consejeros disponibles — {categoria}*\n\n"
            "Puedes contactar directamente a cualquiera de ellos:",
            parse_mode="Markdown",
            reply_markup=kb_categorias_consejeria()
        )

        for c in consejeros:
            texto_consejero = (
                f"👤 *{c['nombre']}*\n"
                f"🏷️ {c.get('descripcion', '')}\n"
            )
            if c.get("telefono"):
                texto_consejero += f"📞 {c['telefono']}\n"

            markup = types.InlineKeyboardMarkup()
            if c.get("telegram"):
                markup.add(types.InlineKeyboardButton(
                    "💬 Escribir en Telegram",
                    url=f"https://t.me/{c['telegram'].lstrip('@')}"
                ))

            bot.send_message(
                message.chat.id,
                texto_consejero,
                parse_mode="Markdown",
                reply_markup=markup if c.get("telegram") else None
            )

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Consejería")
    def volver_consejeria(message):
        seccion_consejeria(message)


# ── Consejeros ────────────────────────────────────────────────────────────────
CONSEJEROS = {
    "Crisis espiritual": [
        # Ejemplo:
        # {
        #     "nombre": "Pastor Juan García",
        #     "descripcion": "Consejero espiritual con 10 años de experiencia",
        #     "telegram": "username_real",
        #     "telefono": "+5312345678",
        # },
    ],
    "Matrimonial": [
        # {
        #     "nombre": "Pastor Pedro Martínez",
        #     "descripcion": "Consejería matrimonial y familiar",
        #     "telegram": "username_real",
        #     "telefono": "+5312345678",
        # },
    ],
    "Personal": [
        # {
        #     "nombre": "Hermana María López",
        #     "descripcion": "Consejería personal y emocional",
        #     "telegram": "username_real",
        #     "telefono": "+5312345678",
        # },
    ],
    "Dudas de fe": [
        # {
        #     "nombre": "Pastor Carlos Rodríguez",
        #     "descripcion": "Apologética y dudas de fe",
        #     "telegram": "username_real",
        #     "telefono": "+5312345678",
        # },
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_categorias_consejeria():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for cat in CATEGORIAS_CONSEJERIA:
        markup.add(types.KeyboardButton(cat))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup
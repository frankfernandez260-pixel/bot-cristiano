from telebot import types
from services.roles import get_or_create_user
from utils.constants import CATEGORIAS_DEBATES
from config.settings import GRUPO_DEBATES_ID

# ── Enlace al grupo de debates (configura el tuyo aquí) ───────────────────────
ENLACE_GRUPO_DEBATES = "https://t.me/+1nXUQ6ZPcYFlYjIx"

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "💬 Debates")
    def seccion_debates(message):
        get_or_create_user(message.from_user)
        bot.send_message(
            message.chat.id,
            "💬 *Debates y Dudas*\n\n"
            "Aquí puedes proponer temas de debate, hacer preguntas "
            "teológicas o compartir dudas de fe con la comunidad.",
            parse_mode="Markdown",
            reply_markup=kb_menu_debates()
        )

    # ── Ir al grupo ───────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔗 Ir al Grupo")
    def ir_al_grupo(message):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "💬 Abrir grupo de debates",
            url=ENLACE_GRUPO_DEBATES
        ))
        bot.send_message(
            message.chat.id,
            "🔗 Únete al grupo de debates y comparte tus ideas con la comunidad:",
            reply_markup=markup
        )

    # ── Proponer tema o duda ──────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "💡 Proponer Tema")
    def proponer_tema(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for cat in CATEGORIAS_DEBATES:
            markup.add(types.KeyboardButton(cat))
        markup.add(types.KeyboardButton("❌ Cancelar"))
        bot.send_message(
            message.chat.id,
            "¿En qué categoría entra tu tema o duda?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, paso_categoria_debate)

    def paso_categoria_debate(message):
        if message.text == "❌ Cancelar":
            seccion_debates(message)
            return

        if message.text not in CATEGORIAS_DEBATES:
            bot.send_message(message.chat.id, "Selecciona una categoría válida.")
            bot.register_next_step_handler(message, paso_categoria_debate)
            return

        categoria = message.text
        bot.send_message(
            message.chat.id,
            f"✍️ Escribe tu tema o duda sobre *{categoria}*:",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(
            message,
            lambda m: paso_texto_debate(m, categoria)
        )

    def paso_texto_debate(message, categoria):
        if message.text == "❌ Cancelar":
            seccion_debates(message)
            return

        if not message.text or len(message.text) < 5:
            bot.send_message(message.chat.id, "Por favor escribe algo más detallado.")
            bot.register_next_step_handler(
                message,
                lambda m: paso_texto_debate(m, categoria)
            )
            return

        usuario = message.from_user
        nombre = f"@{usuario.username}" if usuario.username else usuario.first_name

        texto_grupo = (
            f"💡 *Nueva propuesta de debate*\n\n"
            f"🏷️ Categoría: {categoria}\n"
            f"👤 Propuesto por: {nombre}\n\n"
            f"📝 {message.text}"
        )

        # Enviar al grupo de debates
        try:
            bot.send_message(GRUPO_DEBATES_ID, texto_grupo, parse_mode="Markdown")
        except Exception as e:
            print(f"Error enviando al grupo: {e}")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "💬 Ver en el grupo",
            url=ENLACE_GRUPO_DEBATES
        ))

        bot.send_message(
            message.chat.id,
            "✅ Tu propuesta fue enviada al grupo de debates.\n"
            "¡La comunidad podrá discutirla allí!",
            reply_markup=markup
        )
        bot.send_message(
            message.chat.id,
            "¿Algo más?",
            reply_markup=kb_menu_debates()
        )

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Debates")
    def volver_debates(message):
        seccion_debates(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_debates():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💡 Proponer Tema"),
        types.KeyboardButton("🔗 Ir al Grupo"),
    )
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup
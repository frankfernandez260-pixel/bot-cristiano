from telebot import types
from database.connection import get_session
from database.models import Usuario, IglesiaSeguida, Iglesia
from services.roles import get_or_create_user
from handlers.iglesias import mostrar_iglesia, busqueda_cache
from keyboards.iglesias_kb import kb_navegacion, kb_tarjeta_iglesia

def register(bot):

    @bot.message_handler(func=lambda m: m.text == "⭐ Mis Iglesias")
    def mis_iglesias(message):
        get_or_create_user(message.from_user)
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()

            if not usuario:
                bot.send_message(message.chat.id, "No tienes iglesias seguidas aún.")
                return

            seguidas = session.query(IglesiaSeguida).filter_by(
                user_id=usuario.id
            ).all()

            if not seguidas:
                bot.send_message(
                    message.chat.id,
                    "⭐ Aún no sigues ninguna iglesia.\n\n"
                    "Busca una iglesia y toca *⭐ Seguir Iglesia* para agregarla aquí.",
                    parse_mode="Markdown"
                )
                return

            ids = [s.iglesia_id for s in seguidas]
            iglesias = session.query(Iglesia).filter(
                Iglesia.id.in_(ids),
                Iglesia.activa == True
            ).all()

            if not iglesias:
                bot.send_message(message.chat.id, "No hay iglesias activas en tu lista.")
                return

            busqueda_cache[message.from_user.id] = {
                "resultados": [i.id for i in iglesias],
                "indice": 0,
            }

            bot.send_message(
                message.chat.id,
                f"⭐ Sigues *{len(iglesias)}* iglesia(s).",
                parse_mode="Markdown"
            )
            mostrar_iglesia(
                bot, message.chat.id,
                iglesias[0], 0, len(iglesias),
                message.from_user.id
            )

        finally:
            session.close()
from telebot import types
from database.connection import get_session
from database.models import Usuario, Suscripcion
from services.roles import get_or_create_user, es_admin
import feedparser

# ── Fuentes RSS ───────────────────────────────────────────────────────────────
FUENTES_RSS = [
    {
        "nombre": "ACI Prensa",
        "url": "https://www.aciprensa.com/rss/ultimas.xml",
        "emoji": "🌎"
    },
    {
        "nombre": "Evangelical Focus",
        "url": "https://evangelicalfocus.com/rss",
        "emoji": "✝️"
    },
    {
        "nombre": "Radio Vaticana",
        "url": "https://www.vaticannews.va/es.rss.xml",
        "emoji": "🏛️"
    },
]

def register(bot):

    # ── Entrada ───────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📰 Noticias")
    def seccion_noticias(message):
        get_or_create_user(message.from_user)
        bot.send_message(
            message.chat.id,
            "📰 *Noticias Cristianas*\n\n¿Qué quieres hacer?",
            parse_mode="Markdown",
            reply_markup=kb_menu_noticias()
        )

    # ── Ver últimas noticias ──────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔍 Ver Últimas Noticias")
    def ver_noticias(message):
        bot.send_message(
            message.chat.id,
            "⏳ Buscando noticias...",
        )

        noticias = _obtener_noticias(limite=8)

        if not noticias:
            bot.send_message(
                message.chat.id,
                "😔 No se pudieron obtener noticias en este momento.\n"
                "Verifica tu conexión o intenta más tarde.",
                reply_markup=kb_menu_noticias()
            )
            return

        for noticia in noticias:
            texto = (
                f"{noticia['emoji']} *{noticia['fuente']}*\n\n"
                f"📌 {noticia['titulo']}\n\n"
                f"_{noticia['resumen']}_"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🔗 Leer más",
                url=noticia["link"]
            ))
            bot.send_message(
                message.chat.id,
                texto,
                parse_mode="Markdown",
                reply_markup=markup
            )

        bot.send_message(
            message.chat.id,
            "📰 Esas son las últimas noticias.",
            reply_markup=kb_menu_noticias()
        )

    # ── Suscribirse a noticias diarias ────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📬 Suscribirme")
    def suscribirse(message):
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()
            if not usuario:
                bot.send_message(message.chat.id, "Error de usuario.")
                return

            existente = session.query(Suscripcion).filter_by(
                user_id=usuario.id,
                tipo="noticias",
                activa=True
            ).first()

            if existente:
                bot.send_message(
                    message.chat.id,
                    "⚠️ Ya estás suscrito a las noticias diarias.\n"
                    "Toca *❌ Cancelar Suscripción* si quieres desactivarla.",
                    parse_mode="Markdown",
                    reply_markup=kb_menu_noticias()
                )
                return

            nueva = Suscripcion(
                user_id=usuario.id,
                tipo="noticias",
                activa=True
            )
            session.add(nueva)
            session.commit()

            bot.send_message(
                message.chat.id,
                "✅ ¡Suscrito! Recibirás noticias cristianas cada día.",
                reply_markup=kb_menu_noticias()
            )
        finally:
            session.close()

    # ── Cancelar suscripción ──────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "❌ Cancelar Suscripción")
    def cancelar_suscripcion(message):
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=message.from_user.id
            ).first()
            if not usuario:
                return

            suscripcion = session.query(Suscripcion).filter_by(
                user_id=usuario.id,
                tipo="noticias",
                activa=True
            ).first()

            if not suscripcion:
                bot.send_message(
                    message.chat.id,
                    "⚠️ No tienes una suscripción activa.",
                    reply_markup=kb_menu_noticias()
                )
                return

            suscripcion.activa = False
            session.commit()

            bot.send_message(
                message.chat.id,
                "❌ Suscripción cancelada. Ya no recibirás noticias diarias.",
                reply_markup=kb_menu_noticias()
            )
        finally:
            session.close()

    # ── Volver ────────────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Noticias")
    def volver_noticias(message):
        seccion_noticias(message)


# ── Helpers ───────────────────────────────────────────────────────────────────
def kb_menu_noticias():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔍 Ver Últimas Noticias"),
        types.KeyboardButton("📬 Suscribirme"),
    )
    markup.add(types.KeyboardButton("❌ Cancelar Suscripción"))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup


def _obtener_noticias(limite: int = 8) -> list:
    noticias = []
    por_fuente = limite // len(FUENTES_RSS)

    for fuente in FUENTES_RSS:
        try:
            feed = feedparser.parse(fuente["url"])
            entradas = feed.entries[:por_fuente]
            for entrada in entradas:
                resumen = entrada.get("summary", "")
                # Limpiar HTML básico
                import re
                resumen = re.sub(r"<[^>]+>", "", resumen)
                resumen = resumen[:200] + "..." if len(resumen) > 200 else resumen

                noticias.append({
                    "fuente": fuente["nombre"],
                    "emoji": fuente["emoji"],
                    "titulo": entrada.get("title", "Sin título"),
                    "resumen": resumen,
                    "link": entrada.get("link", ""),
                })
        except Exception:
            continue

    return noticias


def enviar_noticias_diarias(bot):
    """Llamada por APScheduler para enviar noticias a suscriptores."""
    session = get_session()
    try:
        suscripciones = session.query(Suscripcion).filter_by(
            tipo="noticias",
            activa=True
        ).all()

        if not suscripciones:
            return

        noticias = _obtener_noticias(limite=5)
        if not noticias:
            return

        for sus in suscripciones:
            usuario = session.query(Usuario).filter_by(id=sus.user_id).first()
            if not usuario or not usuario.activo:
                continue
            try:
                bot.send_message(
                    usuario.telegram_id,
                    "📰 *Noticias del día* ✝️",
                    parse_mode="Markdown"
                )
                for noticia in noticias:
                    texto = (
                        f"{noticia['emoji']} *{noticia['fuente']}*\n\n"
                        f"📌 {noticia['titulo']}\n\n"
                        f"_{noticia['resumen']}_"
                    )
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(
                        "🔗 Leer más", url=noticia["link"]
                    ))
                    bot.send_message(
                        usuario.telegram_id,
                        texto,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
            except Exception:
                # Si el usuario bloqueó el bot
                usuario.activo = False
                session.commit()
    finally:
        session.close()
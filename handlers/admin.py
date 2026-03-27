from telebot import types
from services.roles import (
    es_admin, asignar_rol, revocar_rol, listar_editores
)
from config.settings import ROLES

def register(bot):

    # ── /autorizar @usuario rol ───────────────────────────────────────────────
    @bot.message_handler(commands=["autorizar"])
    def cmd_autorizar(message):
        if not es_admin(message.from_user.id):
            return

        partes = message.text.split()
        if len(partes) != 3:
            bot.reply_to(
                message,
                f"Uso correcto: /autorizar @usuario rol\n\n"
                f"Roles disponibles:\n" + "\n".join(f"• {r}" for r in ROLES)
            )
            return

        _, username, rol = partes
        username = username.lstrip("@")

        # Buscar el usuario en la BD por username
        from database.connection import get_session
        from database.models import Usuario
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(username=username).first()
            if not usuario:
                bot.reply_to(
                    message,
                    "❌ Usuario no encontrado. Debe haber usado el bot al menos una vez."
                )
                return
            resultado = asignar_rol(usuario.telegram_id, rol, message.from_user.id)
            bot.reply_to(message, resultado)
        finally:
            session.close()

    # ── /revocar @usuario rol ─────────────────────────────────────────────────
    @bot.message_handler(commands=["revocar"])
    def cmd_revocar(message):
        if not es_admin(message.from_user.id):
            return

        partes = message.text.split()
        if len(partes) != 3:
            bot.reply_to(message, "Uso correcto: /revocar @usuario rol")
            return

        _, username, rol = partes
        username = username.lstrip("@")

        from database.connection import get_session
        from database.models import Usuario
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(username=username).first()
            if not usuario:
                bot.reply_to(message, "❌ Usuario no encontrado.")
                return
            resultado = revocar_rol(usuario.telegram_id, rol, message.from_user.id)
            bot.reply_to(message, resultado)
        finally:
            session.close()

    # ── /mis_editores ─────────────────────────────────────────────────────────
    @bot.message_handler(commands=["mis_editores"])
    def cmd_mis_editores(message):
        if not es_admin(message.from_user.id):
            return
        resultado = listar_editores()
        bot.reply_to(message, resultado, parse_mode="Markdown")

    # ── /roles — muestra los roles disponibles ────────────────────────────────
    @bot.message_handler(commands=["roles"])
    def cmd_roles(message):
        if not es_admin(message.from_user.id):
            return
        texto = "📋 *Roles disponibles:*\n\n" + "\n".join(f"• `{r}`" for r in ROLES)
        bot.reply_to(message, texto, parse_mode="Markdown")
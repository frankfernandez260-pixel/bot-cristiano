import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN        = os.getenv("BOT_TOKEN")
ADMIN_ID         = int(os.getenv("ADMIN_ID"))
DATABASE_URL     = os.getenv("DATABASE_URL")          # PostgreSQL en Railway
GRUPO_DEBATES_ID = int(os.getenv("GRUPO_DEBATES_ID", "0"))

# Webhook — Railway genera la URL pública automáticamente
# Ejemplo: https://mi-bot.up.railway.app
WEBHOOK_URL = os.getenv("WEBHOOK_URL")                # Sin barra al final
PORT        = int(os.getenv("PORT", "8000"))          # Railway inyecta PORT solo

# Roles disponibles
ROLES = [
    "moderador",
    "editor_iglesias",
    "editor_eventos",
    "editor_biblioteca",
    "editor_musica",
]

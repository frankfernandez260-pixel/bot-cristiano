import telebot
import uvicorn
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

from config.settings import BOT_TOKEN, WEBHOOK_URL, PORT
from database.models import init_db
from handlers import (
    start, admin, iglesias, mis_iglesias, biblioteca, musica,
    eventos, noticias, testimonios, consejeria, debates, oracion, juegos,
)

# ── Bot ───────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

start.register(bot)
admin.register(bot)
iglesias.register(bot)
mis_iglesias.register(bot)
biblioteca.register(bot)
musica.register(bot)
eventos.register(bot)
noticias.register(bot)
testimonios.register(bot)
consejeria.register(bot)
debates.register(bot)
oracion.register(bot)
juegos.register(bot)

# ── FastAPI ───────────────────────────────────────────────────────────────────
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar: inicializar BD y registrar el webhook con Telegram
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}{WEBHOOK_PATH}")
    print(f"✝️ Bot Cristiano iniciado — webhook activo en {WEBHOOK_URL}{WEBHOOK_PATH}")
    yield
    # Al apagar: eliminar el webhook
    bot.remove_webhook()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Recibe las actualizaciones de Telegram y las procesa."""
    body = await request.body()
    update = telebot.types.Update.de_json(body.decode("utf-8"))
    bot.process_new_updates([update])
    return Response(status_code=200)

@app.get("/")
async def health():
    """Health check para Railway."""
    return {"status": "ok", "bot": "Bot Cristiano"}

# ── Arranque ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)

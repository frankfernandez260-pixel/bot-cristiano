from telebot import types
from utils.constants import (
    TIPOS_IGLESIA, DENOMINACIONES,
    PROVINCIAS, PROVINCIAS_MUNICIPIOS
)

# ── Menú de la sección Iglesias ───────────────────────────────────────────────
def kb_menu_iglesias():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔍 Buscar Iglesia"),
        types.KeyboardButton("📍 Buscar por Ubicación"),
    )
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup


# ── Tipo de iglesia ───────────────────────────────────────────────────────────
def kb_tipo_iglesia():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for tipo in TIPOS_IGLESIA:
        markup.add(types.KeyboardButton(tipo))
    markup.add(types.KeyboardButton("🔙 Atrás"))
    return markup


# ── Opciones protestante ──────────────────────────────────────────────────────
def kb_opciones_protestante():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("🔍 Buscar por Denominación"),
        types.KeyboardButton("🌐 Explorar sin Denominación"),
    )
    markup.add(types.KeyboardButton("🔙 Atrás"))
    return markup


# ── Denominaciones ────────────────────────────────────────────────────────────
def kb_denominaciones():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for den in DENOMINACIONES:
        markup.add(types.KeyboardButton(den))
    markup.add(types.KeyboardButton("🔙 Atrás"))
    return markup


# ── Provincias ────────────────────────────────────────────────────────────────
def kb_provincias():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for provincia in PROVINCIAS:
        markup.add(types.KeyboardButton(provincia))
    markup.add(types.KeyboardButton("🔙 Atrás"))
    return markup


# ── Municipios ────────────────────────────────────────────────────────────────
def kb_municipios(provincia: str):
    municipios = PROVINCIAS_MUNICIPIOS.get(provincia, [])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for municipio in municipios:
        markup.add(types.KeyboardButton(municipio))
    markup.add(types.KeyboardButton("🔙 Atrás"))
    return markup


# ── Botones inline de la tarjeta de iglesia ───────────────────────────────────
def kb_tarjeta_iglesia(iglesia_id: int, siguiendo: bool = False):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_seguir = types.InlineKeyboardButton(
        "💔 Dejar de Seguir" if siguiendo else "⭐ Seguir Iglesia",
        callback_data=f"iglesia_seguir_{iglesia_id}"
    )
    btn_horarios = types.InlineKeyboardButton(
        "🕐 Horarios", callback_data=f"iglesia_horarios_{iglesia_id}"
    )
    btn_ministerios = types.InlineKeyboardButton(
        "🙌 Ministerios", callback_data=f"iglesia_ministerios_{iglesia_id}"
    )
    btn_ubicacion = types.InlineKeyboardButton(
        "📍 Ubicación", callback_data=f"iglesia_ubicacion_{iglesia_id}"
    )
    btn_telefonos = types.InlineKeyboardButton(
        "📞 Teléfonos", callback_data=f"iglesia_telefonos_{iglesia_id}"
    )
    btn_eventos = types.InlineKeyboardButton(
        "🎉 Eventos", callback_data=f"iglesia_eventos_{iglesia_id}"
    )
    btn_comunicados = types.InlineKeyboardButton(
        "📢 Comunicados", callback_data=f"iglesia_comunicados_{iglesia_id}"
    )

    markup.add(btn_seguir)
    markup.add(btn_horarios, btn_ministerios)
    markup.add(btn_ubicacion, btn_telefonos)
    markup.add(btn_eventos, btn_comunicados)

    return markup


# ── Navegación entre iglesias (anterior / siguiente) ──────────────────────────
def kb_navegacion(indice: int, total: int, prefijo: str = "nav"):
    markup = types.InlineKeyboardMarkup(row_width=3)
    botones = []

    if indice > 0:
        botones.append(types.InlineKeyboardButton(
            "⬅️ Anterior", callback_data=f"{prefijo}_{indice - 1}"
        ))

    botones.append(types.InlineKeyboardButton(
        f"{indice + 1} / {total}", callback_data="nav_info"
    ))

    if indice < total - 1:
        botones.append(types.InlineKeyboardButton(
            "Siguiente ➡️", callback_data=f"{prefijo}_{indice + 1}"
        ))

    markup.add(*botones)
    return markup


# ── Botones de evento especial ────────────────────────────────────────────────
def kb_evento(evento_id: int, inscrito: bool = False, recordatorio: bool = False):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_inscribir = types.InlineKeyboardButton(
        "✅ Anotado" if inscrito else "📝 Anotarme",
        callback_data=f"evento_inscribir_{evento_id}"
    )
    btn_recordatorio = types.InlineKeyboardButton(
        "🔔 Recordatorio ✅" if recordatorio else "🔔 Recordatorio",
        callback_data=f"evento_recordatorio_{evento_id}"
    )

    markup.add(btn_inscribir, btn_recordatorio)
    return markup


# ── Pedir ubicación ───────────────────────────────────────────────────────────
def kb_pedir_ubicacion():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton(
        "📍 Enviar mi Ubicación",
        request_location=True
    ))
    markup.add(types.KeyboardButton("🔙 Atrás"))
    return markup


# ── Menú de registro de iglesia (para editores) ───────────────────────────────
def kb_confirmar_iglesia():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Publicar", callback_data="reg_iglesia_publicar"),
        types.InlineKeyboardButton("❌ Cancelar", callback_data="reg_iglesia_cancelar"),
    )
    return markup
    
def kb_menu_iglesias_editor():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔍 Buscar Iglesia"),
        types.KeyboardButton("📍 Buscar por Ubicación"),
    )
    markup.add(types.KeyboardButton("➕ Nueva Iglesia"))
    markup.add(types.KeyboardButton("🔙 Menú Principal"))
    return markup
from telebot import types
from database.connection import get_session
from database.models import (
    Iglesia, IglesiaSeguida, Ministerio,
    Evento, Comunicado, Usuario, EventoInscrito
)
from services.roles import get_or_create_user, tiene_rol, es_admin
from services.geo import iglesias_cercanas, formato_distancia
from keyboards.iglesias_kb import (
    kb_menu_iglesias, kb_tipo_iglesia, kb_opciones_protestante,
    kb_denominaciones, kb_provincias, kb_municipios,
    kb_tarjeta_iglesia, kb_navegacion, kb_evento,
    kb_pedir_ubicacion, kb_confirmar_iglesia
)
from utils.constants import (
    TIPOS_IGLESIA, DENOMINACIONES, PROVINCIAS,
    PROVINCIAS_MUNICIPIOS
)
from datetime import datetime

# ── Cache de búsqueda y registro ──────────────────────────────────────────────
busqueda_cache = {}
registro_cache = {}

# ── Helper: mostrar tarjeta de iglesia ────────────────────────────────────────
def mostrar_iglesia(bot, chat_id, iglesia, indice, total, user_telegram_id):
    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(
            telegram_id=user_telegram_id
        ).first()

        siguiendo = False
        if usuario:
            sig = session.query(IglesiaSeguida).filter_by(
                user_id=usuario.id,
                iglesia_id=iglesia.id
            ).first()
            siguiendo = sig is not None

        denominacion = f" · {iglesia.denominacion}" if iglesia.denominacion else ""
        distancia = f"\n📏 A {formato_distancia(iglesia.distancia_km)}" if hasattr(iglesia, "distancia_km") else ""

        texto = (
            f"🏛️ *{iglesia.nombre}*\n"
            f"_{iglesia.tipo}{denominacion}_\n\n"
            f"📍 {iglesia.direccion or 'Dirección no disponible'}\n"
            f"🗺️ {iglesia.provincia}, {iglesia.municipio}"
            f"{distancia}\n\n"
            f"{iglesia.descripcion or ''}"
        )

        markup = kb_tarjeta_iglesia(iglesia.id, siguiendo)
        if total > 1:
            nav = kb_navegacion(indice, total, prefijo="nav_iglesia")
            for row in nav.keyboard:
                markup.keyboard.append(row)

        if iglesia.fotos and len(iglesia.fotos) > 0:
            if len(iglesia.fotos) == 1:
                bot.send_photo(
                    chat_id, iglesia.fotos[0],
                    caption=texto, parse_mode="Markdown",
                    reply_markup=markup
                )
            else:
                media = [types.InputMediaPhoto(fid) for fid in iglesia.fotos]
                media[0].caption = texto
                media[0].parse_mode = "Markdown"
                bot.send_media_group(chat_id, media)
                bot.send_message(chat_id, "👇 Opciones:", reply_markup=markup)
        else:
            bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=markup)

    finally:
        session.close()


def register(bot):

    # ── Entrada a la sección ──────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🏛️ Iglesias")
    def seccion_iglesias(message):
        get_or_create_user(message.from_user)
        from keyboards.iglesias_kb import kb_menu_iglesias_editor
        es_ed = tiene_rol(message.from_user.id, "editor_iglesias") or es_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "🏛️ *Iglesias*\n\nExplora y conoce iglesias en Cuba.",
            parse_mode="Markdown",
            reply_markup=kb_menu_iglesias_editor() if es_ed else kb_menu_iglesias()
        )

    # ── Buscar iglesia ────────────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔍 Buscar Iglesia")
    def buscar_iglesia(message):
        busqueda_cache[message.from_user.id] = {}
        bot.send_message(
            message.chat.id,
            "¿Qué tipo de iglesia buscas?",
            reply_markup=kb_tipo_iglesia()
        )
        bot.register_next_step_handler(message, paso_tipo)

    # ── Buscar por ubicación ──────────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "📍 Buscar por Ubicación")
    def buscar_por_ubicacion(message):
        bot.send_message(
            message.chat.id,
            "📍 Envía tu ubicación y te mostraré las iglesias más cercanas.",
            reply_markup=kb_pedir_ubicacion()
        )
        bot.register_next_step_handler(message, paso_ubicacion)

    # ── Paso: recibir ubicación ───────────────────────────────────────────────
    def paso_ubicacion(message):
        if message.text == "🔙 Atrás":
            bot.send_message(message.chat.id, "🏛️ Iglesias", reply_markup=kb_menu_iglesias())
            return

        if not message.location:
            bot.send_message(message.chat.id, "Por favor envía tu ubicación usando el botón.")
            bot.register_next_step_handler(message, paso_ubicacion)
            return

        lat = message.location.latitude
        lon = message.location.longitude

        session = get_session()
        try:
            iglesias = session.query(Iglesia).filter_by(activa=True).all()
            if not iglesias:
                bot.send_message(
                    message.chat.id,
                    "😔 No hay iglesias registradas aún.",
                    reply_markup=kb_menu_iglesias()
                )
                return

            cercanas = iglesias_cercanas(lat, lon, iglesias)
            busqueda_cache[message.from_user.id] = {
                "resultados": [i.id for i in cercanas],
                "indice": 0,
            }

            bot.send_message(
                message.chat.id,
                f"✅ Encontré *{len(cercanas)}* iglesia(s) cerca de ti.",
                parse_mode="Markdown",
                reply_markup=kb_menu_iglesias()
            )
            mostrar_iglesia(bot, message.chat.id, cercanas[0], 0, len(cercanas), message.from_user.id)

        finally:
            session.close()

    # ── Paso 1: tipo de iglesia ───────────────────────────────────────────────
    def paso_tipo(message):
        if message.text == "🔙 Atrás":
            bot.send_message(message.chat.id, "🏛️ Iglesias", reply_markup=kb_menu_iglesias())
            return

        if message.text not in TIPOS_IGLESIA:
            bot.send_message(message.chat.id, "Por favor selecciona una opción válida.")
            bot.register_next_step_handler(message, paso_tipo)
            return

        busqueda_cache[message.from_user.id]["tipo"] = message.text

        if message.text == "Evangélica / Protestante":
            bot.send_message(
                message.chat.id,
                "¿Cómo quieres buscar?",
                reply_markup=kb_opciones_protestante()
            )
            bot.register_next_step_handler(message, paso_opcion_protestante)
        else:
            bot.send_message(
                message.chat.id,
                "¿En qué provincia?",
                reply_markup=kb_provincias()
            )
            bot.register_next_step_handler(message, paso_provincia)

    # ── Paso 2a: opción protestante ───────────────────────────────────────────
    def paso_opcion_protestante(message):
        if message.text == "🔙 Atrás":
            bot.send_message(message.chat.id, "¿Qué tipo de iglesia buscas?", reply_markup=kb_tipo_iglesia())
            bot.register_next_step_handler(message, paso_tipo)
            return

        if message.text == "🔍 Buscar por Denominación":
            bot.send_message(
                message.chat.id,
                "¿Qué denominación?",
                reply_markup=kb_denominaciones()
            )
            bot.register_next_step_handler(message, paso_denominacion)

        elif message.text == "🌐 Explorar sin Denominación":
            busqueda_cache[message.from_user.id]["denominacion"] = None
            bot.send_message(
                message.chat.id,
                "¿En qué provincia?",
                reply_markup=kb_provincias()
            )
            bot.register_next_step_handler(message, paso_provincia)
        else:
            bot.send_message(message.chat.id, "Por favor selecciona una opción válida.")
            bot.register_next_step_handler(message, paso_opcion_protestante)

    # ── Paso 2b: denominación ─────────────────────────────────────────────────
    def paso_denominacion(message):
        if message.text == "🔙 Atrás":
            bot.send_message(message.chat.id, "¿Cómo quieres buscar?", reply_markup=kb_opciones_protestante())
            bot.register_next_step_handler(message, paso_opcion_protestante)
            return

        if message.text not in DENOMINACIONES:
            bot.send_message(message.chat.id, "Por favor selecciona una denominación válida.")
            bot.register_next_step_handler(message, paso_denominacion)
            return

        busqueda_cache[message.from_user.id]["denominacion"] = message.text
        bot.send_message(
            message.chat.id,
            "¿En qué provincia?",
            reply_markup=kb_provincias()
        )
        bot.register_next_step_handler(message, paso_provincia)

    # ── Paso 3: provincia ─────────────────────────────────────────────────────
    def paso_provincia(message):
        if message.text == "🔙 Atrás":
            cache = busqueda_cache.get(message.from_user.id, {})
            if cache.get("tipo") == "Evangélica / Protestante":
                bot.send_message(message.chat.id, "¿Cómo quieres buscar?", reply_markup=kb_opciones_protestante())
                bot.register_next_step_handler(message, paso_opcion_protestante)
            else:
                bot.send_message(message.chat.id, "¿Qué tipo de iglesia buscas?", reply_markup=kb_tipo_iglesia())
                bot.register_next_step_handler(message, paso_tipo)
            return

        if message.text not in PROVINCIAS:
            bot.send_message(message.chat.id, "Por favor selecciona una provincia válida.")
            bot.register_next_step_handler(message, paso_provincia)
            return

        busqueda_cache[message.from_user.id]["provincia"] = message.text
        bot.send_message(
            message.chat.id,
            "¿En qué municipio?",
            reply_markup=kb_municipios(message.text)
        )
        bot.register_next_step_handler(message, paso_municipio)

    # ── Paso 4: municipio → buscar y mostrar ──────────────────────────────────
    def paso_municipio(message):
        if message.text == "🔙 Atrás":
            cache = busqueda_cache.get(message.from_user.id, {})
            provincia = cache.get("provincia", "")
            bot.send_message(message.chat.id, "¿En qué provincia?", reply_markup=kb_provincias())
            bot.register_next_step_handler(message, paso_provincia)
            return

        cache = busqueda_cache.get(message.from_user.id, {})
        provincia = cache.get("provincia", "")
        municipios_validos = PROVINCIAS_MUNICIPIOS.get(provincia, [])

        if message.text not in municipios_validos:
            bot.send_message(message.chat.id, "Por favor selecciona un municipio válido.")
            bot.register_next_step_handler(message, paso_municipio)
            return

        cache["municipio"] = message.text
        busqueda_cache[message.from_user.id] = cache

        session = get_session()
        try:
            query = session.query(Iglesia).filter(
                Iglesia.activa == True,
                Iglesia.provincia == cache.get("provincia"),
                Iglesia.municipio == cache.get("municipio"),
            )

            if cache.get("tipo"):
                query = query.filter(Iglesia.tipo == cache["tipo"])

            if cache.get("denominacion"):
                query = query.filter(Iglesia.denominacion == cache["denominacion"])

            iglesias = query.all()

            if not iglesias:
                bot.send_message(
                    message.chat.id,
                    "😔 No encontré iglesias con esos filtros.\n"
                    "Prueba con otros criterios.",
                    reply_markup=kb_menu_iglesias()
                )
                return

            busqueda_cache[message.from_user.id]["resultados"] = [i.id for i in iglesias]
            busqueda_cache[message.from_user.id]["indice"] = 0

            bot.send_message(
                message.chat.id,
                f"✅ Encontré *{len(iglesias)}* iglesia(s).",
                parse_mode="Markdown",
                reply_markup=kb_menu_iglesias()
            )
            mostrar_iglesia(
                bot, message.chat.id,
                iglesias[0], 0, len(iglesias),
                message.from_user.id
            )

        finally:
            session.close()

    # ── Navegación entre resultados ───────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("nav_iglesia_"))
    def navegar_iglesias(call):
        indice = int(call.data.split("_")[-1])
        cache = busqueda_cache.get(call.from_user.id, {})
        ids = cache.get("resultados", [])

        if not ids or indice >= len(ids):
            bot.answer_callback_query(call.id)
            return

        session = get_session()
        try:
            iglesia = session.query(Iglesia).filter_by(id=ids[indice]).first()
            if not iglesia:
                bot.answer_callback_query(call.id, "Iglesia no encontrada.")
                return

            busqueda_cache[call.from_user.id]["indice"] = indice
            bot.answer_callback_query(call.id)
            mostrar_iglesia(
                bot, call.message.chat.id,
                iglesia, indice, len(ids),
                call.from_user.id
            )
        finally:
            session.close()

    # ── Seguir / Dejar de seguir ──────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_seguir_"))
    def toggle_seguir(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=call.from_user.id
            ).first()
            if not usuario:
                bot.answer_callback_query(call.id, "Error de usuario.")
                return

            existente = session.query(IglesiaSeguida).filter_by(
                user_id=usuario.id,
                iglesia_id=iglesia_id
            ).first()

            if existente:
                session.delete(existente)
                session.commit()
                bot.answer_callback_query(call.id, "💔 Dejaste de seguir esta iglesia.")
            else:
                nueva = IglesiaSeguida(user_id=usuario.id, iglesia_id=iglesia_id)
                session.add(nueva)
                session.commit()
                bot.answer_callback_query(call.id, "⭐ ¡Ahora sigues esta iglesia!")

            siguiendo = not bool(existente)
            cache = busqueda_cache.get(call.from_user.id, {})
            ids = cache.get("resultados", [iglesia_id])
            indice = cache.get("indice", 0)

            nuevo_markup = kb_tarjeta_iglesia(iglesia_id, siguiendo)
            if len(ids) > 1:
                nav = kb_navegacion(indice, len(ids), prefijo="nav_iglesia")
                for row in nav.keyboard:
                    nuevo_markup.keyboard.append(row)

            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=nuevo_markup
            )
        finally:
            session.close()

    # ── Horarios ──────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_horarios_"))
    def ver_horarios(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            iglesia = session.query(Iglesia).filter_by(id=iglesia_id).first()
            if not iglesia or not iglesia.horario:
                bot.answer_callback_query(call.id, "No hay horarios registrados aún.")
                return

            lineas = [f"🕐 *Horarios de {iglesia.nombre}*\n"]
            for dia, hora in iglesia.horario.items():
                lineas.append(f"• {dia}: {hora}")

            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "\n".join(lineas),
                parse_mode="Markdown"
            )
        finally:
            session.close()

    # ── Ministerios ───────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_ministerios_"))
    def ver_ministerios(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            ministerios = session.query(Ministerio).filter_by(iglesia_id=iglesia_id).all()
            if not ministerios:
                bot.answer_callback_query(call.id, "No hay ministerios registrados.")
                return

            bot.answer_callback_query(call.id)
            for min in ministerios:
                texto = f"🙌 *{min.nombre}*\n\n{min.descripcion or ''}"
                markup = types.InlineKeyboardMarkup()
                if min.contacto_telegram:
                    markup.add(types.InlineKeyboardButton(
                        "📩 Contactar",
                        url=f"https://t.me/{min.contacto_telegram.lstrip('@')}"
                    ))
                bot.send_message(
                    call.message.chat.id,
                    texto,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
        finally:
            session.close()

    # ── Ubicación ─────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_ubicacion_"))
    def ver_ubicacion(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            iglesia = session.query(Iglesia).filter_by(id=iglesia_id).first()
            if not iglesia:
                bot.answer_callback_query(call.id, "Iglesia no encontrada.")
                return
            bot.answer_callback_query(call.id)
            bot.send_location(call.message.chat.id, iglesia.latitud, iglesia.longitud)
            bot.send_message(call.message.chat.id, f"📍 {iglesia.direccion or iglesia.nombre}")
        finally:
            session.close()

    # ── Teléfonos ─────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_telefonos_"))
    def ver_telefonos(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            iglesia = session.query(Iglesia).filter_by(id=iglesia_id).first()
            if not iglesia or not iglesia.telefonos:
                bot.answer_callback_query(call.id, "No hay teléfonos registrados.")
                return
            bot.answer_callback_query(call.id)
            lineas = [f"📞 *Contactos de {iglesia.nombre}*\n"]
            for tel in iglesia.telefonos:
                lineas.append(f"• {tel}")
            bot.send_message(
                call.message.chat.id,
                "\n".join(lineas),
                parse_mode="Markdown"
            )
        finally:
            session.close()

    # ── Comunicados ───────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_comunicados_"))
    def ver_comunicados(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            ahora = datetime.utcnow()
            comunicados = session.query(Comunicado).filter(
                Comunicado.iglesia_id == iglesia_id,
                Comunicado.fecha_expiracion > ahora
            ).order_by(Comunicado.fecha_creacion.desc()).all()

            if not comunicados:
                bot.answer_callback_query(call.id, "No hay comunicados recientes.")
                return

            bot.answer_callback_query(call.id)
            for com in comunicados:
                fecha = com.fecha_creacion.strftime("%d/%m/%Y")
                bot.send_message(
                    call.message.chat.id,
                    f"📢 *Comunicado del {fecha}*\n\n{com.texto}",
                    parse_mode="Markdown"
                )
        finally:
            session.close()

    # ── Eventos de iglesia ────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("iglesia_eventos_"))
    def ver_eventos_iglesia(call):
        iglesia_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            ahora = datetime.utcnow()
            eventos = session.query(Evento).filter(
                Evento.iglesia_id == iglesia_id,
                Evento.fecha_evento >= ahora
            ).order_by(Evento.fecha_evento).all()

            if not eventos:
                bot.answer_callback_query(call.id, "No hay eventos próximos.")
                return

            bot.answer_callback_query(call.id)
            usuario = session.query(Usuario).filter_by(
                telegram_id=call.from_user.id
            ).first()

            for ev in eventos:
                fecha = ev.fecha_evento.strftime("%d/%m/%Y %H:%M")
                inscrito = False
                recordatorio = False

                if usuario:
                    ins = session.query(EventoInscrito).filter_by(
                        user_id=usuario.id,
                        evento_id=ev.id
                    ).first()
                    if ins:
                        inscrito = True
                        recordatorio = ins.recordatorio

                texto = (
                    f"🎉 *{ev.titulo}*\n"
                    f"📅 {fecha}\n\n"
                    f"{ev.descripcion or ''}"
                )
                markup = kb_evento(ev.id, inscrito, recordatorio)

                if ev.imagen_file_id:
                    bot.send_photo(
                        call.message.chat.id,
                        ev.imagen_file_id,
                        caption=texto,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                else:
                    bot.send_message(
                        call.message.chat.id,
                        texto,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
        finally:
            session.close()

    # ── Inscribirse a evento ──────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("evento_inscribir_"))
    def toggle_inscribir(call):
        evento_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=call.from_user.id
            ).first()
            if not usuario:
                bot.answer_callback_query(call.id, "Error de usuario.")
                return

            existente = session.query(EventoInscrito).filter_by(
                user_id=usuario.id,
                evento_id=evento_id
            ).first()

            if existente:
                session.delete(existente)
                session.commit()
                bot.answer_callback_query(call.id, "❌ Te desinscribiste del evento.")
            else:
                nuevo = EventoInscrito(user_id=usuario.id, evento_id=evento_id)
                session.add(nuevo)
                session.commit()
                bot.answer_callback_query(call.id, "✅ ¡Te anotaste al evento!")
        finally:
            session.close()

    # ── Recordatorio de evento ────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda c: c.data.startswith("evento_recordatorio_"))
    def toggle_recordatorio(call):
        evento_id = int(call.data.split("_")[-1])
        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                telegram_id=call.from_user.id
            ).first()
            if not usuario:
                bot.answer_callback_query(call.id)
                return

            ins = session.query(EventoInscrito).filter_by(
                user_id=usuario.id,
                evento_id=evento_id
            ).first()

            if not ins:
                ins = EventoInscrito(
                    user_id=usuario.id,
                    evento_id=evento_id,
                    recordatorio=True
                )
                session.add(ins)
                session.commit()
                bot.answer_callback_query(call.id, "🔔 Recordatorio activado.")
            else:
                ins.recordatorio = not ins.recordatorio
                session.commit()
                estado = "activado" if ins.recordatorio else "desactivado"
                bot.answer_callback_query(call.id, f"🔔 Recordatorio {estado}.")
        finally:
            session.close()

# ── Registro de iglesia (solo editores) ───────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "➕ Nueva Iglesia")
    def nueva_iglesia(message):
        if not tiene_rol(message.from_user.id, "editor_iglesias") and not es_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ No tienes permiso para registrar iglesias.")
            return

        registro_cache[message.from_user.id] = {}
        bot.send_message(
            message.chat.id,
            "🏛️ *Registrar nueva iglesia*\n\n¿Cuál es el nombre de la iglesia?",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, reg_nombre)

    def reg_nombre(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        registro_cache[message.from_user.id]["nombre"] = message.text
        bot.send_message(
            message.chat.id,
            "¿Qué tipo de iglesia es?",
            reply_markup=kb_tipo_iglesia()
        )
        bot.register_next_step_handler(message, reg_tipo)

    def reg_tipo(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if message.text not in TIPOS_IGLESIA:
            bot.send_message(message.chat.id, "Por favor selecciona un tipo válido.")
            bot.register_next_step_handler(message, reg_tipo)
            return

        registro_cache[message.from_user.id]["tipo"] = message.text

        if message.text == "Evangélica / Protestante":
            bot.send_message(
                message.chat.id,
                "¿Qué denominación?",
                reply_markup=kb_denominaciones()
            )
            bot.register_next_step_handler(message, reg_denominacion)
        else:
            registro_cache[message.from_user.id]["denominacion"] = None
            bot.send_message(
                message.chat.id,
                "¿En qué provincia está la iglesia?",
                reply_markup=kb_provincias()
            )
            bot.register_next_step_handler(message, reg_provincia)

    def reg_denominacion(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if message.text not in DENOMINACIONES:
            bot.send_message(message.chat.id, "Por favor selecciona una denominación válida.")
            bot.register_next_step_handler(message, reg_denominacion)
            return

        registro_cache[message.from_user.id]["denominacion"] = message.text
        bot.send_message(
            message.chat.id,
            "¿En qué provincia está la iglesia?",
            reply_markup=kb_provincias()
        )
        bot.register_next_step_handler(message, reg_provincia)

    def reg_provincia(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if message.text not in PROVINCIAS:
            bot.send_message(message.chat.id, "Por favor selecciona una provincia válida.")
            bot.register_next_step_handler(message, reg_provincia)
            return

        registro_cache[message.from_user.id]["provincia"] = message.text
        bot.send_message(
            message.chat.id,
            "¿En qué municipio?",
            reply_markup=kb_municipios(message.text)
        )
        bot.register_next_step_handler(message, reg_municipio)

    def reg_municipio(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        cache = registro_cache.get(message.from_user.id, {})
        provincia = cache.get("provincia", "")
        municipios_validos = PROVINCIAS_MUNICIPIOS.get(provincia, [])

        if message.text not in municipios_validos:
            bot.send_message(message.chat.id, "Por favor selecciona un municipio válido.")
            bot.register_next_step_handler(message, reg_municipio)
            return

        registro_cache[message.from_user.id]["municipio"] = message.text
        bot.send_message(
            message.chat.id,
            "📍 Ahora envía la ubicación de la iglesia.\n"
            "Puedes moverla en el mapa para colocarla exactamente.",
            reply_markup=kb_pedir_ubicacion()
        )
        bot.register_next_step_handler(message, reg_ubicacion)

    def reg_ubicacion(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if not message.location:
            bot.send_message(
                message.chat.id,
                "Por favor envía la ubicación usando el botón 📍",
            )
            bot.register_next_step_handler(message, reg_ubicacion)
            return

        registro_cache[message.from_user.id]["latitud"] = message.location.latitude
        registro_cache[message.from_user.id]["longitud"] = message.location.longitude

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "✅ Ubicación guardada.\n\n"
            "¿Cuál es la dirección textual? (ej: Calle 5 #23 entre A y B)\n"
            "O toca *Omitir* para continuar.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_direccion)

    def reg_direccion(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if message.text != "⏭️ Omitir":
            registro_cache[message.from_user.id]["direccion"] = message.text
        else:
            registro_cache[message.from_user.id]["direccion"] = None

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "¿Tienes una descripción para la iglesia?\n"
            "O toca *Omitir* para continuar.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, reg_descripcion)

    def reg_descripcion(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if message.text != "⏭️ Omitir":
            registro_cache[message.from_user.id]["descripcion"] = message.text
        else:
            registro_cache[message.from_user.id]["descripcion"] = None

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⏭️ Omitir"))
        bot.send_message(
            message.chat.id,
            "📸 Envía las fotos de la iglesia una por una.\n"
            "Cuando termines escribe *listo* o toca *Omitir*.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        registro_cache[message.from_user.id]["fotos"] = []
        bot.register_next_step_handler(message, reg_fotos)

    def reg_fotos(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        cache = registro_cache.get(message.from_user.id, {})

        if message.text and message.text.lower() in ["listo", "⏭️ omitir"]:
            # Pasar a teléfonos
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("⏭️ Omitir"))
            bot.send_message(
                message.chat.id,
                "📞 ¿Tienes teléfonos o contactos?\n"
                "Escríbelos separados por comas o toca *Omitir*.",
                parse_mode="Markdown",
                reply_markup=markup
            )
            bot.register_next_step_handler(message, reg_telefonos)
            return

        if message.photo:
            file_id = message.photo[-1].file_id
            cache["fotos"].append(file_id)
            registro_cache[message.from_user.id] = cache
            bot.send_message(
                message.chat.id,
                f"✅ Foto {len(cache['fotos'])} guardada. "
                "Envía otra o escribe *listo*.",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(message, reg_fotos)
        else:
            bot.send_message(message.chat.id, "Por favor envía una foto o escribe *listo*.", parse_mode="Markdown")
            bot.register_next_step_handler(message, reg_fotos)

    def reg_telefonos(message):
        if message.text == "/cancelar":
            bot.send_message(message.chat.id, "❌ Registro cancelado.", reply_markup=kb_menu_iglesias())
            registro_cache.pop(message.from_user.id, None)
            return

        if message.text != "⏭️ Omitir":
            telefonos = [t.strip() for t in message.text.split(",")]
            registro_cache[message.from_user.id]["telefonos"] = telefonos
        else:
            registro_cache[message.from_user.id]["telefonos"] = []

        # Mostrar preview y confirmar
        _mostrar_preview_iglesia(bot, message)

    def _mostrar_preview_iglesia(bot, message):
        cache = registro_cache.get(message.from_user.id, {})

        denominacion = f" · {cache.get('denominacion')}" if cache.get("denominacion") else ""
        fotos_count = len(cache.get("fotos", []))

        texto = (
            f"📋 *Vista previa*\n\n"
            f"🏛️ *{cache.get('nombre')}*\n"
            f"_{cache.get('tipo')}{denominacion}_\n\n"
            f"🗺️ {cache.get('provincia')}, {cache.get('municipio')}\n"
            f"📍 {cache.get('direccion') or 'Sin dirección textual'}\n"
            f"📸 {fotos_count} foto(s)\n"
            f"📞 {', '.join(cache.get('telefonos', [])) or 'Sin teléfonos'}\n\n"
            f"{cache.get('descripcion') or ''}\n\n"
            f"¿Publicar esta iglesia?"
        )

        bot.send_message(
            message.chat.id,
            texto,
            parse_mode="Markdown",
            reply_markup=kb_confirmar_iglesia()
        )

    @bot.callback_query_handler(func=lambda c: c.data == "reg_iglesia_publicar")
    def confirmar_publicar(call):
        cache = registro_cache.get(call.from_user.id, {})
        if not cache:
            bot.answer_callback_query(call.id, "Sesión expirada, empieza de nuevo.")
            return

        session = get_session()
        try:
            from database.models import Usuario
            usuario = session.query(Usuario).filter_by(
                telegram_id=call.from_user.id
            ).first()

            nueva = Iglesia(
                nombre=cache.get("nombre"),
                tipo=cache.get("tipo"),
                denominacion=cache.get("denominacion"),
                provincia=cache.get("provincia"),
                municipio=cache.get("municipio"),
                latitud=cache.get("latitud"),
                longitud=cache.get("longitud"),
                descripcion=cache.get("descripcion"),
                direccion=cache.get("direccion"),
                fotos=cache.get("fotos", []),
                telefonos=cache.get("telefonos", []),
                publicado_por=usuario.id if usuario else None,
                activa=True,
            )
            session.add(nueva)
            session.commit()

            registro_cache.pop(call.from_user.id, None)
            bot.answer_callback_query(call.id, "✅ Iglesia publicada.")
            bot.send_message(
                call.message.chat.id,
                "✅ *¡Iglesia publicada exitosamente!*\n"
                "Ya aparece en las búsquedas.",
                parse_mode="Markdown",
                reply_markup=kb_menu_iglesias()
            )
        finally:
            session.close()

    @bot.callback_query_handler(func=lambda c: c.data == "reg_iglesia_cancelar")
    def confirmar_cancelar(call):
        registro_cache.pop(call.from_user.id, None)
        bot.answer_callback_query(call.id, "❌ Registro cancelado.")
        bot.send_message(
            call.message.chat.id,
            "❌ Registro cancelado.",
            reply_markup=kb_menu_iglesias()
        )

    # ── Volver al menú principal ──────────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text == "🔙 Menú Principal")
    def volver_menu(message):
        from handlers.start import menu_principal
        bot.send_message(
            message.chat.id,
            "Menú principal 👇",
            reply_markup=menu_principal(message.from_user.id)
        )
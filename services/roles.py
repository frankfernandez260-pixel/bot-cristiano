from database.connection import get_session
from database.models import Usuario, Rol
from config.settings import ADMIN_ID, ROLES

# ── Obtener o crear usuario ───────────────────────────────────────────────────
def get_or_create_user(telegram_user):
    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(
            telegram_id=telegram_user.id
        ).first()

        if not usuario:
            usuario = Usuario(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                nombre=telegram_user.first_name,
            )
            session.add(usuario)
            session.commit()
            session.refresh(usuario)

        return usuario.id
    finally:
        session.close()

# ── Verificar si es admin ─────────────────────────────────────────────────────
def es_admin(telegram_id: int) -> bool:
    return telegram_id == ADMIN_ID

# ── Verificar si tiene un rol específico ─────────────────────────────────────
def tiene_rol(telegram_id: int, rol: str) -> bool:
    if es_admin(telegram_id):
        return True

    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(
            telegram_id=telegram_id
        ).first()

        if not usuario:
            return False

        rol_encontrado = session.query(Rol).filter_by(
            user_id=usuario.id,
            rol=rol
        ).first()

        return rol_encontrado is not None
    finally:
        session.close()

# ── Verificar si puede publicar contenido (cualquier rol de editor) ───────────
def es_editor(telegram_id: int) -> bool:
    if es_admin(telegram_id):
        return True

    roles_editor = [
        "editor_iglesias",
        "editor_eventos",
        "editor_biblioteca",
        "editor_musica",
        "moderador",
    ]

    return any(tiene_rol(telegram_id, r) for r in roles_editor)

# ── Asignar rol ───────────────────────────────────────────────────────────────
def asignar_rol(telegram_id_objetivo: int, rol: str, admin_telegram_id: int) -> str:
    if not es_admin(admin_telegram_id):
        return "❌ No tienes permiso para asignar roles."

    if rol not in ROLES:
        return f"❌ Rol inválido. Roles disponibles: {', '.join(ROLES)}"

    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(
            telegram_id=telegram_id_objetivo
        ).first()

        if not usuario:
            return "❌ Usuario no encontrado. El usuario debe haber usado el bot al menos una vez."

        admin = session.query(Usuario).filter_by(
            telegram_id=admin_telegram_id
        ).first()

        # Verificar si ya tiene ese rol
        existente = session.query(Rol).filter_by(
            user_id=usuario.id,
            rol=rol
        ).first()

        if existente:
            return f"⚠️ @{usuario.username or usuario.nombre} ya tiene el rol {rol}."

        nuevo_rol = Rol(
            user_id=usuario.id,
            rol=rol,
            asignado_por=admin.id if admin else None,
        )
        session.add(nuevo_rol)
        session.commit()

        return f"✅ Rol {rol} asignado a @{usuario.username or usuario.nombre}."
    finally:
        session.close()

# ── Revocar rol ───────────────────────────────────────────────────────────────
def revocar_rol(telegram_id_objetivo: int, rol: str, admin_telegram_id: int) -> str:
    if not es_admin(admin_telegram_id):
        return "❌ No tienes permiso para revocar roles."

    session = get_session()
    try:
        usuario = session.query(Usuario).filter_by(
            telegram_id=telegram_id_objetivo
        ).first()

        if not usuario:
            return "❌ Usuario no encontrado."

        rol_obj = session.query(Rol).filter_by(
            user_id=usuario.id,
            rol=rol
        ).first()

        if not rol_obj:
            return f"⚠️ @{usuario.username or usuario.nombre} no tiene el rol {rol}."

        session.delete(rol_obj)
        session.commit()

        return f"✅ Rol {rol} revocado a @{usuario.username or usuario.nombre}."
    finally:
        session.close()

# ── Listar todos los editores ─────────────────────────────────────────────────
def listar_editores() -> str:
    session = get_session()
    try:
        roles = session.query(Rol).all()

        if not roles:
            return "No hay editores asignados aún."

        lines = ["👥 *Editores autorizados:*\n"]
        for r in roles:
            usuario = session.query(Usuario).filter_by(id=r.user_id).first()
            nombre = f"@{usuario.username}" if usuario.username else usuario.nombre
            lines.append(f"• {nombre} — `{r.rol}`")

        return "\n".join(lines)
    finally:
        session.close()
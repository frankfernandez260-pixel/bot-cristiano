from sqlalchemy import (
    create_engine, Column, Integer, BigInteger,
    String, Text, Boolean, Float, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timedelta
from database.connection import engine

Base = declarative_base()

# ── Usuarios ──────────────────────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id            = Column(Integer, primary_key=True)
    telegram_id   = Column(BigInteger, unique=True, nullable=False)
    username      = Column(String, nullable=True)
    nombre        = Column(String, nullable=True)
    fecha_registro= Column(DateTime, default=datetime.utcnow)
    activo        = Column(Boolean, default=True)

    roles             = relationship("Rol", back_populates="usuario", foreign_keys="Rol.user_id")
    iglesias_seguidas = relationship("IglesiaSeguida", back_populates="usuario")

# ── Roles ─────────────────────────────────────────────────────────────────────
class Rol(Base):
    __tablename__ = "roles"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    rol         = Column(String, nullable=False)
    asignado_por= Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha       = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", foreign_keys=[user_id], back_populates="roles")

# ── Iglesias ──────────────────────────────────────────────────────────────────
class Iglesia(Base):
    __tablename__ = "iglesias"

    id            = Column(Integer, primary_key=True)
    nombre        = Column(String, nullable=False)
    tipo          = Column(String, nullable=False)
    denominacion  = Column(String, nullable=True)
    provincia     = Column(String, nullable=False)
    municipio     = Column(String, nullable=False)
    latitud       = Column(Float, nullable=False)
    longitud      = Column(Float, nullable=False)
    descripcion   = Column(Text, nullable=True)
    direccion     = Column(Text, nullable=True)
    fotos         = Column(JSON, default=list)
    telefonos     = Column(JSON, default=list)
    horario       = Column(JSON, default=dict)
    publicado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    activa        = Column(Boolean, default=True)
    fecha_creacion= Column(DateTime, default=datetime.utcnow)

    ministerios  = relationship("Ministerio", back_populates="iglesia")
    eventos      = relationship("Evento", back_populates="iglesia")
    comunicados  = relationship("Comunicado", back_populates="iglesia")
    seguidores   = relationship("IglesiaSeguida", back_populates="iglesia")

# ── Iglesias seguidas ─────────────────────────────────────────────────────────
class IglesiaSeguida(Base):
    __tablename__ = "iglesias_seguidas"

    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    iglesia_id     = Column(Integer, ForeignKey("iglesias.id"), nullable=False)
    notificaciones = Column(Boolean, default=True)
    fecha          = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="iglesias_seguidas")
    iglesia = relationship("Iglesia", back_populates="seguidores")

# ── Ministerios ───────────────────────────────────────────────────────────────
class Ministerio(Base):
    __tablename__ = "ministerios"

    id                = Column(Integer, primary_key=True)
    iglesia_id        = Column(Integer, ForeignKey("iglesias.id"), nullable=False)
    nombre            = Column(String, nullable=False)
    descripcion       = Column(Text, nullable=True)
    contacto_telegram = Column(String, nullable=True)

    iglesia = relationship("Iglesia", back_populates="ministerios")

# ── Eventos ───────────────────────────────────────────────────────────────────
class Evento(Base):
    __tablename__ = "eventos"

    id              = Column(Integer, primary_key=True)
    iglesia_id      = Column(Integer, ForeignKey("iglesias.id"), nullable=True)
    titulo          = Column(String, nullable=False)
    descripcion     = Column(Text, nullable=True)
    imagen_file_id  = Column(String, nullable=True)
    fecha_evento    = Column(DateTime, nullable=False)
    provincia       = Column(String, nullable=True)
    publicado_por   = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_creacion  = Column(DateTime, default=datetime.utcnow)

    iglesia  = relationship("Iglesia", back_populates="eventos")
    inscritos= relationship("EventoInscrito", back_populates="evento")

# ── Eventos inscritos ─────────────────────────────────────────────────────────
class EventoInscrito(Base):
    __tablename__ = "eventos_inscritos"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    evento_id    = Column(Integer, ForeignKey("eventos.id"), nullable=False)
    recordatorio = Column(Boolean, default=True)
    fecha        = Column(DateTime, default=datetime.utcnow)

    evento = relationship("Evento", back_populates="inscritos")

# ── Comunicados ───────────────────────────────────────────────────────────────
class Comunicado(Base):
    __tablename__ = "comunicados"

    id               = Column(Integer, primary_key=True)
    iglesia_id       = Column(Integer, ForeignKey("iglesias.id"), nullable=False)
    texto            = Column(Text, nullable=False)
    fecha_creacion   = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))

    iglesia = relationship("Iglesia", back_populates="comunicados")

# ── Biblioteca ────────────────────────────────────────────────────────────────
class ArchivosBiblioteca(Base):
    __tablename__ = "archivos_biblioteca"

    id        = Column(Integer, primary_key=True)
    tipo      = Column(String, nullable=False)
    titulo    = Column(String, nullable=False)
    autor     = Column(String, nullable=True)
    version   = Column(String, nullable=True)
    file_id   = Column(String, nullable=False)
    subido_por= Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha     = Column(DateTime, default=datetime.utcnow)

# ── Música ────────────────────────────────────────────────────────────────────
class Cancion(Base):
    __tablename__ = "canciones"

    id        = Column(Integer, primary_key=True)
    titulo    = Column(String, nullable=False)
    artista   = Column(String, nullable=True)
    genero    = Column(String, nullable=True)
    file_id   = Column(String, nullable=False)
    subido_por= Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha     = Column(DateTime, default=datetime.utcnow)

# ── Testimonios ───────────────────────────────────────────────────────────────
class Testimonio(Base):
    __tablename__ = "testimonios"

    id               = Column(Integer, primary_key=True)
    user_id          = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    anonimo          = Column(Boolean, default=False)
    categoria        = Column(String, nullable=True)
    texto            = Column(Text, nullable=False)
    foto_file_id     = Column(String, nullable=True)
    aprobado         = Column(Boolean, default=False)
    fecha_creacion   = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

# ── Oraciones ─────────────────────────────────────────────────────────────────
class Oracion(Base):
    __tablename__ = "oraciones"

    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    anonimo        = Column(Boolean, default=False)
    texto          = Column(Text, nullable=False)
    contador_oro   = Column(Integer, default=0)
    activa         = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

# ── Preguntas vistas ──────────────────────────────────────────────────────────
class PreguntaVista(Base):
    __tablename__ = "preguntas_vistas"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    pregunta_id = Column(String, nullable=False)   # ID del JSON, sin FK a BD
    juego       = Column(String, nullable=False)
    fecha       = Column(DateTime, default=datetime.utcnow)

# ── Ranking ───────────────────────────────────────────────────────────────────
class Ranking(Base):
    __tablename__ = "ranking"

    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    juego     = Column(String, nullable=False)
    puntaje   = Column(Integer, default=0)
    nivel_max = Column(Integer, default=0)
    fecha     = Column(DateTime, default=datetime.utcnow)

# ── Versículo del día ─────────────────────────────────────────────────────────
class VersiculoDia(Base):
    __tablename__ = "versiculos_dia"

    id         = Column(Integer, primary_key=True)
    texto      = Column(Text, nullable=False)
    referencia = Column(String, nullable=False)
    fecha_uso  = Column(DateTime, nullable=True)

# ── Suscripciones ─────────────────────────────────────────────────────────────
class Suscripcion(Base):
    __tablename__ = "suscripciones"

    id      = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo    = Column(String, nullable=False)
    activa  = Column(Boolean, default=True)
    fecha   = Column(DateTime, default=datetime.utcnow)

# ── Crear todas las tablas ────────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(engine)

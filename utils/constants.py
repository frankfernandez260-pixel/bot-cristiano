# ── Tipos de iglesia ──────────────────────────────────────────────────────────
TIPOS_IGLESIA = [
    "Evangélica / Protestante",
    "Católica",
    "Interdenominacional",
]

# ── Denominaciones protestantes ───────────────────────────────────────────────
DENOMINACIONES = [
    "Bautista",
    "Metodista",
    "Presbiteriana",
    "Pentecostal",
    "Adventista",
    "Episcopal / Anglicana",
    "Otra",
]

# ── Provincias y municipios de Cuba ───────────────────────────────────────────
PROVINCIAS_MUNICIPIOS = {
    "Pinar del Río": [
        "Consolación del Sur", "Guane", "La Palma", "Los Palacios",
        "Mantua", "Minas de Matahambre", "Pinar del Río", "San Luis",
        "Sandino", "Viñales",
    ],
    "Artemisa": [
        "Alquízar", "Artemisa", "Bauta", "Caimito", "Guanajay",
        "Güira de Melena", "Mariel", "San Antonio de los Baños",
        "San Cristóbal", "Bahía Honda", "Candelaria",
    ],
    "La Habana": [
        "Arroyo Naranjo", "Boyeros", "Centro Habana", "Cerro",
        "Cotorro", "Diez de Octubre", "Guanabacoa", "Habana del Este",
        "Habana Vieja", "La Lisa", "Marianao", "Playa", "Plaza",
        "Regla", "San Miguel del Padrón",
    ],
    "Mayabeque": [
        "Batabanó", "Bejucal", "Güines", "Jaruco", "Madruga",
        "Melena del Sur", "Nueva Paz", "Quivicán", "San José de las Lajas",
        "San Nicolás", "Santa Cruz del Norte",
    ],
    "Matanzas": [
        "Calimete", "Cárdenas", "Ciénaga de Zapata", "Colón",
        "Jagüey Grande", "Jovellanos", "Limonar", "Los Arabos",
        "Matanzas", "Pedro Betancourt", "Perico", "Unión de Reyes",
    ],
    "Villa Clara": [
        "Caibarién", "Camajuaní", "Cifuentes", "Corralillo",
        "Encrucijada", "Manicaragua", "Placetas", "Quemado de Güines",
        "Ranchuelo", "Remedios", "sagua la Grande", "Santa Clara",
        "Santo Domingo",
    ],
    "Cienfuegos": [
        "Abreus", "Aguada de Pasajeros", "Cienfuegos", "Cruces",
        "Cumanayagua", "Lajas", "Palmira", "Rodas",
    ],
    "Sancti Spíritus": [
        "Cabaiguán", "Fomento", "Jatibonico", "La Sierpe",
        "Sancti Spíritus", "Trinidad", "Yaguajay",
    ],
    "Ciego de Ávila": [
        "Baraguá", "Bolivia", "Chambas", "Ciego de Ávila",
        "Ciro Redondo", "Florencia", "Majagua", "Morón",
        "Primero de Enero", "Venezuela",
    ],
    "Camagüey": [
        "Camagüey", "Carlos Manuel de Céspedes", "Esmeralda",
        "Florida", "Guáimaro", "Jimaguayú", "Minas", "Najasa",
        "Nuevitas", "Santa Cruz del Sur", "Sibanicú",
        "Sierra de Cubitas", "Vertientes",
    ],
    "Las Tunas": [
        "Amancio", "Colombia", "Jesús Menéndez", "JobaBo",
        "Las Tunas", "Majibacoa", "Manatí", "Puerto Padre",
    ],
    "Holguín": [
        "Antilla", "Báguanos", "Banes", "Cacocum", "Calixto García",
        "Cueto", "Frank País", "Gibara", "Holguín", "Mayarí",
        "Moa", "Rafael Freyre", "Sagua de Tánamo", "Urbano Noris",
    ],
    "Granma": [
        "Bartolomé Masó", "Bayamo", "Buey Arriba", "Campechuela",
        "Cauto Cristo", "Guisa", "Jiguaní", "Manzanillo",
        "Media Luna", "Niquero", "Pilón", "Río Cauto", "Yara",
    ],
    "Santiago de Cuba": [
        "Contramaestre", "Guamá", "Mella", "Palma Soriano",
        "San Luis", "Santiago de Cuba", "Segundo Frente",
        "Songo-La Maya", "Tercer Frente",
    ],
    "Guantánamo": [
        "Baracoa", "Caimanera", "El Salvador", "Guantánamo",
        "Imías", "Maisí", "Manuel Tames", "Niceto Pérez",
        "San Antonio del Sur", "Yateras",
    ],
    "Isla de la Juventud": [
        "Isla de la Juventud",
    ],
}

PROVINCIAS = list(PROVINCIAS_MUNICIPIOS.keys())

# ── Géneros musicales ─────────────────────────────────────────────────────────
GENEROS_MUSICA = [
    "Himnos clásicos",
    "Alabanza contemporánea",
    "Música infantil",
    "Instrumental / Meditación",
]

# ── Categorías de testimonios ─────────────────────────────────────────────────
CATEGORIAS_TESTIMONIO = [
    "Sanidad",
    "Conversión",
    "Milagro",
    "Restauración",
    "Provisión",
    "Otro",
]

# ── Categorías de consejería ──────────────────────────────────────────────────
CATEGORIAS_CONSEJERIA = [
    "Crisis espiritual",
    "Matrimonial",
    "Personal",
    "Dudas de fe",
]

# ── Categorías de debates ─────────────────────────────────────────────────────
CATEGORIAS_DEBATES = [
    "Teología",
    "Vida cristiana",
    "Dudas de fe",
    "Apologética",
]

# ── Tipos de biblioteca ───────────────────────────────────────────────────────
TIPOS_BIBLIOTECA = [
    "biblia",
    "literatura",
    "catecismo",
    "devocional",
]

# ── Salvavidas del millonario ─────────────────────────────────────────────────
SALVAVIDAS_MILLONARIO = [5, 10, 13]

# ── Niveles del millonario ────────────────────────────────────────────────────
NIVELES_MILLONARIO = {
    1:  "🥉 Bronce I",
    2:  "🥉 Bronce II",
    3:  "🥉 Bronce III",
    4:  "🥈 Plata I",
    5:  "🥈 Plata II  ⚓",
    6:  "🥈 Plata III",
    7:  "🥇 Oro I",
    8:  "🥇 Oro II",
    9:  "🥇 Oro III",
    10: "💎 Diamante I  ⚓",
    11: "💎 Diamante II",
    12: "💎 Diamante III",
    13: "👑 Maestro I  ⚓",
    14: "👑 Maestro II",
    15: "👑 Maestro Bíblico",
}
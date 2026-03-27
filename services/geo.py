import math

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en kilómetros entre dos coordenadas GPS.
    """
    R = 6371  # Radio de la Tierra en km

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return round(R * c, 2)


def iglesias_cercanas(user_lat: float, user_lon: float, iglesias: list, limite: int = 10) -> list:
    """
    Recibe una lista de objetos Iglesia y los devuelve ordenados por cercanía.
    Agrega el atributo 'distancia_km' a cada iglesia.
    limite: cuántas iglesias devolver como máximo.
    """
    resultados = []

    for iglesia in iglesias:
        distancia = haversine(user_lat, user_lon, iglesia.latitud, iglesia.longitud)
        iglesia.distancia_km = distancia
        resultados.append(iglesia)

    resultados.sort(key=lambda i: i.distancia_km)

    return resultados[:limite]


def formato_distancia(km: float) -> str:
    """
    Formatea la distancia para mostrar al usuario.
    Menos de 1 km → metros. Más de 1 km → kilómetros.
    """
    if km < 1:
        metros = int(km * 1000)
        return f"{metros} m"
    return f"{km} km"
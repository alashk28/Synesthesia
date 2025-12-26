import requests

# TU CONFIGURACIÓN
API_KEY = "ea36d8e248dadb8ed7c8bb82e7804f75"
BASE_URL = "https://api.themoviedb.org/3"

# --- EL PUENTE LÓGICO (MÚSICA -> CINE) ---
# Aquí definimos qué género de cine corresponde a cada estilo musical.
# Puedes agregar más si tus compañeros te pasan otros géneros.
MOOD_MAP = {
    "pop": 35,          # Pop -> Comedia (Diversión, ligero)
    "rock": 28,         # Rock -> Acción (Energía, adrenalina)
    "reggaeton": 12,    # Reggaeton -> Aventura (Fiesta, movimiento)
    "indie": 18,        # Indie -> Drama (Profundo, emocional)
    "sad": 10749,       # Música Triste -> Romance/Melodrama
    "electronic": 878,  # Electrónica -> Ciencia Ficción (Futurista)
    "metal": 27         # Metal -> Terror (Intenso, oscuro)
}

def obtener_recomendaciones(genero_musical):
    """
    Recibe un género musical (string), busca su equivalente en cine
    y devuelve una lista de películas recomendadas y populares.
    """
    # 1. Traducir música a ID de cine
    genero_musical = genero_musical.lower()
    if genero_musical not in MOOD_MAP:
        print(f"⚠ El género '{genero_musical}' no está mapeado. Usando 'Pop' por defecto.")
        id_cine = 35 # Default: Comedia
    else:
        id_cine = MOOD_MAP[genero_musical]

    # 2. Consultar a la API de TMDB (Con filtros de calidad)
    # Filtramos: En español, ordenado por popularidad, y que tenga mínimo 500 votos (para evitar pelis desconocidas)
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": API_KEY,
        "language": "es-ES",
        "sort_by": "popularity.desc", 
        "include_adult": "false",
        "include_video": "false",
        "page": 1,
        "with_genres": id_cine,
        "vote_count.gte": 500  # TRUCO: Solo películas con más de 500 votos (evita basura)
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Avisar si hay error de conexión
        data = response.json()
        
        peliculas = []
        for p in data['results'][:5]: # Tomamos las Top 5
            peliculas.append({
                "Titulo": p['title'],
                "Fecha": p.get('release_date', 'N/A').split('-')[0],
                "Rating": p['vote_average'],
                "Sinopsis": p['overview'][:150] + "..." # Cortamos la sinopsis para que no sea enorme
            })
        return peliculas

    except Exception as e:
        print(f"Error conectando con TMDB: {e}")
        return []

# --- PRUEBA DEL SISTEMA ---
# Simulamos que tu compañero te pasa estos datos de Spotify:
musica_usuario = "Rock" 

print(f"🎧 El usuario escucha: {musica_usuario}")
print(f"🎬 Buscando películas compatibles...")
print("-" * 50)

resultados = obtener_recomendaciones(musica_usuario)

for i, peli in enumerate(resultados, 1):
    print(f"{i}. {peli['Titulo']} ({peli['Fecha']}) - ⭐ {peli['Rating']}")
    print(f"   Resumen: {peli['Sinopsis']}\n")
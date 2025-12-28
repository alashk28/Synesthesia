import os
import logging
import requests  # <--- Esta es la librería nueva
from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from collections import Counter
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CREDENCIALES ---
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')  # <--- Aquí usará la clave que pegaste

# Verificación de seguridad
if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, TMDB_API_KEY]):
    raise ValueError("Faltan variables en el .env. Revisa que TMDB_API_KEY esté bien guardada.")

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_super_segura_fija')

# --- DICCIONARIO TRADUCTOR (Spotify -> IDs de Cine) ---
GENRE_MAPPING = {
    "Pop": "10402,35,10749",       # Música, Comedia, Romance
    "Rock": "10402,18,99",         # Música, Drama, Documental
    "Hip Hop": "10402,80,18",      # Música, Crimen, Drama
    "Hip-Hop": "10402,80,18",
    "Electronic": "878,53,28",     # Sci-Fi, Thriller, Acción
    "Dance": "10402,35",
    "Indie": "18,35,10749",        # Drama, Comedia, Romance
    "Metal": "27,28,53",           # Terror, Acción, Thriller
    "R&B": "10402,10749,18",
    "Reggaeton": "10402,28,35",
    "Jazz": "10402,18,36",
    "Classical": "36,18"
}

# --- FUNCIONES ---

def get_genres_from_artists(sp, artist_ids):
    genres = []
    for artist_id in artist_ids:
        try:
            artist = sp.artist(artist_id)
            genres.extend(artist['genres'])
        except Exception as e:
            logger.warning(f"Error con artista {artist_id}: {e}")
    return genres

def get_top_genres(sp, limit=50):
    try:
        results = sp.current_user_top_artists(limit=limit)
        artist_ids = [item['id'] for item in results['items']]
        all_genres = get_genres_from_artists(sp, artist_ids)
        
        # Limpieza de géneros para que coincidan con nuestro mapa
        cleaned_genres = []
        for g in all_genres:
            found = False
            for key in GENRE_MAPPING.keys():
                if key.lower() in g.lower():
                    cleaned_genres.append(key)
                    found = True
                    break
            if not found:
                cleaned_genres.append("Pop") # Si no sabemos qué es, asumimos Pop

        genre_counts = Counter(cleaned_genres)
        top_genres = [genre for genre, count in genre_counts.most_common(5)]
        
        # SI ES CUENTA NUEVA (LISTA VACÍA)
        if not top_genres:
            return ["Pop", "Rock", "Hip-Hop", "Electronic"]
            
        return top_genres
    except Exception as e:
        logger.error(f"Error obteniendo géneros: {e}")
        return ["Pop", "Rock", "Hip-Hop", "Electronic"]

def get_movies_from_tmdb(genre_name):
    """Conecta con la API de TMDB y descarga películas reales"""
    try:
        # 1. Obtener los IDs numéricos del género
        tmdb_genre_ids = GENRE_MAPPING.get(genre_name, "10402")
        
        # 2. Configurar la petición a la API
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "es-ES",           # En Español
            "sort_by": "popularity.desc",  # Las más famosas
            "with_genres": tmdb_genre_ids, # Del género correcto
            "vote_count.gte": 200          # Que tengan suficientes votos
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        movies = []
        if "results" in data:
            for item in data["results"][:6]: # Guardamos las 6 mejores
                poster_path = item.get("poster_path")
                # Construimos la url completa de la imagen
                full_image_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Image"
                
                movies.append({
                    "title": item.get("title"),
                    "year": item.get("release_date", "N/A")[:4],
                    "image": full_image_url, # <--- La imagen viene directo de TMDB
                    "overview": item.get("overview", "")
                })
        return movies
    except Exception as e:
        logger.error(f"Error conectando a TMDB: {e}")
        return []

def get_movie_recommendations(user_genres):
    recommendations = {}
    for genre in user_genres:
        # Llama a la función que conecta a internet
        movies = get_movies_from_tmdb(genre)
        if movies:
            recommendations[genre] = movies
    return recommendations

# --- RUTAS ---
@app.route('/')
def index():
    return render_template('index.html', logged_in=False, mood_name="Inicia sesión", user_name="Usuario")

@app.route('/login')
def login():
    cache_handler = FlaskSessionCacheHandler(session)
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope='user-top-read', cache_handler=cache_handler)
    return redirect(sp_oauth.get_authorize_url())

@app.route('/callback')
def callback():
    cache_handler = FlaskSessionCacheHandler(session)
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope='user-top-read', cache_handler=cache_handler)
    code = request.args.get('code')
    
    try:
        sp_oauth.get_access_token(code)
        if not sp_oauth.validate_token(cache_handler.get_cached_token()):
            raise Exception("Token inválido")
            
        sp = spotipy.Spotify(auth_manager=sp_oauth)
        user = sp.current_user()
        
        # 1. Obtener géneros
        top_genres = get_top_genres(sp)
        
        # 2. Buscar películas en TMDB (Internet)
        movie_recommendations = get_movie_recommendations(top_genres)
        
        return render_template('index.html', logged_in=True, mood_name="Cinéfilo Musical", movie_recommendations=movie_recommendations, top_genres=top_genres, user_name=user['display_name'])

    except Exception as e:
        logger.error(f"Error en callback: {e}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
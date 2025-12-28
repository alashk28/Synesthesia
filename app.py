import os
import logging
import requests
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
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# Verificación de seguridad
if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, TMDB_API_KEY]):
    raise ValueError("FALTAN VARIABLES EN EL ENV DE RENDER")

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_default_insegura')

# --- TRADUCTOR (SPOTIFY -> CINE) ---
GENRE_MAPPING = {
    "Pop": "10402,35,10749", "Rock": "10402,18,99", "Hip Hop": "10402,80,18",
    "Hip-Hop": "10402,80,18", "Electronic": "878,53,28", "Dance": "10402,35",
    "Indie": "18,35,10749", "Metal": "27,28,53", "R&B": "10402,10749,18",
    "Reggaeton": "10402,28,35", "Jazz": "10402,18,36", "Classical": "36,18"
}

# --- FUNCIONES ---

def get_movies_from_tmdb(genre_name):
    """Busca películas en TMDB (Internet)"""
    try:
        tmdb_genre_ids = GENRE_MAPPING.get(genre_name, "10402")
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY, "language": "es-ES",
            "sort_by": "popularity.desc", "with_genres": tmdb_genre_ids,
            "vote_count.gte": 200
        }
        # Timeout de 3 seg para que no se congele
        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        movies = []
        if "results" in data:
            for item in data["results"][:6]:
                poster = item.get("poster_path")
                img = f"https://image.tmdb.org/t/p/w500{poster}" if poster else "https://via.placeholder.com/500"
                movies.append({
                    "title": item.get("title"), 
                    "year": item.get("release_date", "")[:4],
                    "image": img, 
                    "overview": item.get("overview", "")
                })
        return movies
    except Exception as e:
        logger.error(f"Error TMDB: {e}")
        return []

def get_movie_recommendations(user_genres):
    """ESTA ES LA FUNCIÓN QUE FALTABA: Une géneros con películas"""
    recommendations = {}
    for genre in user_genres:
        movies = get_movies_from_tmdb(genre)
        if movies:
            recommendations[genre] = movies
    return recommendations

def get_top_genres(sp):
    """Obtiene los géneros favoritos"""
    try:
        results = sp.current_user_top_artists(limit=20, time_range='medium_term')
        artist_ids = [item['id'] for item in results['items']]
        
        cleaned_genres = []
        if artist_ids:
            # Pedimos detalles en lotes pequeños
            full_artists = sp.artists(artist_ids[:20])
            for artist in full_artists['artists']:
                for g in artist['genres']:
                    # Buscamos coincidencias con nuestro mapa
                    for key in GENRE_MAPPING.keys():
                        if key.lower() in g.lower():
                            cleaned_genres.append(key)
                            break
                            
        genre_counts = Counter(cleaned_genres)
        top = [g for g, c in genre_counts.most_common(5)]
        return top if top else ["Pop", "Rock"]
    except Exception as e:
        logger.error(f"Error Géneros: {e}")
        return ["Pop", "Rock"]

def get_audio_analysis(sp):
    """Analiza la intensidad (Blindado contra errores)"""
    try:
        top = sp.current_user_top_tracks(limit=10, time_range='short_term')
        # Filtramos canciones locales (sin ID)
        ids = [t['id'] for t in top['items'] if t.get('id')]
        
        if not ids: return {}, {}
        
        features = sp.audio_features(ids)
        avg = {'danceability':0, 'energy':0, 'valence':0, 'acousticness':0}
        c = 0
        for f in features:
            if f:
                for k in avg: avg[k] += f[k]
                c += 1
        
        if c > 0:
            for k in avg: avg[k] = round(avg[k]/c, 2)
            
        scores = {
            'Positividad': int(avg['valence']*100),
            'Energía': int(avg['energy']*100),
            'Ritmo': int(avg['danceability']*100),
            'Acústico': int(avg['acousticness']*100)
        }
        return scores, avg
    except Exception as e:
        logger.error(f"Error Audio: {e}")
        return {}, {}

# --- RUTAS ---
@app.route('/')
def index():
    return render_template('index.html', logged_in=False, mood_name="Login", mood_scores={}, audio_analysis={}, movie_recommendations={}, top_genres=[], user_name="")

@app.route('/login')
def login():
    handler = FlaskSessionCacheHandler(session)
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope='user-top-read', cache_handler=handler, show_dialog=True)
    return redirect(sp_oauth.get_authorize_url())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    try:
        handler = FlaskSessionCacheHandler(session)
        sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope='user-top-read', cache_handler=handler)
        
        code = request.args.get('code')
        if not code: return "Error: Sin código de Spotify"

        sp_oauth.get_access_token(code)
        if not sp_oauth.validate_token(handler.get_cached_token()):
             return "Error: Token inválido"

        sp = spotipy.Spotify(auth_manager=sp_oauth)
        user = sp.current_user()
        
        # Ejecución principal
        top_genres = get_top_genres(sp)
        # Aquí es donde fallaba antes, ahora ya existe la función:
        movie_recommendations = get_movie_recommendations(top_genres)
        mood_scores, audio_analysis = get_audio_analysis(sp)
        
        mood_name = "Oyente Equilibrado"
        if mood_scores.get('Energía', 0) > 75: mood_name = "Explosión de Energía"
        
        return render_template('index.html', logged_in=True, mood_name=mood_name, mood_scores=mood_scores, audio_analysis=audio_analysis, movie_recommendations=movie_recommendations, top_genres=top_genres, user_name=user['display_name'])

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        # Si falla, mostramos el error en pantalla para arreglarlo rápido
        return f"""
        <div style="color: red; padding: 20px; border: 2px solid red;">
            <h2>❌ Algo falló</h2>
            <p>{e}</p>
            <a href='/login'>Reintentar</a>
        </div>
        """

if __name__ == '__main__':
    app.run(debug=True)
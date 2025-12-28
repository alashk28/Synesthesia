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

if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, TMDB_API_KEY]):
    raise ValueError("Faltan variables en el .env.")

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_segura_123')

# --- TRADUCTOR DE GÉNEROS ---
GENRE_MAPPING = {
    "Pop": "10402,35,10749",
    "Rock": "10402,18,99",
    "Hip Hop": "10402,80,18",
    "Hip-Hop": "10402,80,18",
    "Electronic": "878,53,28",
    "Dance": "10402,35",
    "Indie": "18,35,10749",
    "Metal": "27,28,53",
    "R&B": "10402,10749,18",
    "Reggaeton": "10402,28,35",
    "Jazz": "10402,18,36",
    "Classical": "36,18"
}

# --- FUNCIONES DE CINE (TMDB) ---
def get_movies_from_tmdb(genre_name):
    try:
        tmdb_genre_ids = GENRE_MAPPING.get(genre_name, "10402")
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "es-ES",
            "sort_by": "popularity.desc",
            "with_genres": tmdb_genre_ids,
            "vote_count.gte": 200
        }
        response = requests.get(url, params=params, timeout=5) # Timeout para que no se cuelgue
        data = response.json()
        movies = []
        if "results" in data:
            for item in data["results"][:6]:
                poster_path = item.get("poster_path")
                full_image_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Image"
                movies.append({
                    "title": item.get("title"),
                    "year": item.get("release_date", "N/A")[:4],
                    "image": full_image_url,
                    "overview": item.get("overview", "")
                })
        return movies
    except Exception as e:
        logger.error(f"Error conectando a TMDB: {e}")
        return []

# --- FUNCIONES DE SPOTIFY ---
def get_genres_from_artists(sp, artist_ids):
    genres = []
    # Procesamos en lotes pequeños para evitar errores
    for i in range(0, len(artist_ids), 50):
        batch = artist_ids[i:i+50]
        try:
            artists_full = sp.artists(batch) # Llamada eficiente en lote
            for artist in artists_full['artists']:
                if artist:
                    genres.extend(artist['genres'])
        except Exception as e:
            logger.warning(f"Error recuperando artistas: {e}")
    return genres

def get_top_genres(sp):
    try:
        results = sp.current_user_top_artists(limit=50, time_range='medium_term')
        artist_ids = [item['id'] for item in results['items']]
        all_genres = get_genres_from_artists(sp, artist_ids)
        
        cleaned_genres = []
        for g in all_genres:
            found = False
            for key in GENRE_MAPPING.keys():
                if key.lower() in g.lower():
                    cleaned_genres.append(key)
                    found = True
                    break
            if not found:
                cleaned_genres.append("Pop")

        genre_counts = Counter(cleaned_genres)
        top_genres = [genre for genre, count in genre_counts.most_common(5)]
        return top_genres if top_genres else ["Pop", "Rock"]
    except Exception as e:
        logger.error(f"Error géneros: {e}")
        return ["Pop"]

def get_audio_analysis(sp):
    """VERSIÓN BLINDADA: Si falla, devuelve ceros pero NO rompe la app"""
    try:
        top_tracks = sp.current_user_top_tracks(limit=20, time_range='short_term')
        
        # Filtramos canciones que no tengan ID (archivos locales)
        track_ids = []
        if top_tracks and 'items' in top_tracks:
            for t in top_tracks['items']:
                if t and t.get('id'): # Solo si tiene ID válido
                    track_ids.append(t['id'])
        
        if not track_ids:
            return {}, {}

        # Intentamos obtener audio features
        try:
            audio_features = sp.audio_features(track_ids)
        except Exception as e:
            logger.error(f"Error interno de Spotify (Audio Features): {e}")
            return {}, {} # Si falla aquí, devolvemos vacío y seguimos
        
        avg_features = {'danceability': 0, 'energy': 0, 'valence': 0, 'acousticness': 0}
        count = 0
        
        for f in audio_features:
            if f: # Verificamos que no sea None
                avg_features['danceability'] += f['danceability']
                avg_features['energy'] += f['energy']
                avg_features['valence'] += f['valence']
                avg_features['acousticness'] += f['acousticness']
                count += 1
        
        if count > 0:
            for key in avg_features:
                avg_features[key] = round(avg_features[key] / count, 2)

        mood_scores = {
            'Positividad': int(avg_features['valence'] * 100),
            'Energía': int(avg_features['energy'] * 100),
            'Ritmo': int(avg_features['danceability'] * 100),
            'Acústico': int(avg_features['acousticness'] * 100)
        }
        return mood_scores, avg_features

    except Exception as e:
        logger.error(f"Error GENERAL en análisis de audio: {e}")
        # Retorno de emergencia para que la app cargue sí o sí
        return {}, {} 

# --- RUTAS ---
@app.route('/')
def index():
    return render_template('index.html', logged_in=False, mood_name="Inicia sesión", mood_scores={}, audio_analysis={}, movie_recommendations={}, top_genres=[], user_name="Usuario")

@app.route('/login')
def login():
    cache_handler = FlaskSessionCacheHandler(session)
    # Agregamos show_dialog=True para forzar que te pregunte cuenta si es necesario
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope='user-top-read', cache_handler=cache_handler, show_dialog=True)
    return redirect(sp_oauth.get_authorize_url())

@app.route('/logout')
def logout():
    session.clear() # Borra la sesión de la app
    return redirect(url_for('index'))

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
        
        top_genres = get_top_genres(sp)
        movie_recommendations = get_movie_recommendations(top_genres)
        mood_scores, audio_analysis = get_audio_analysis(sp) # Ahora esta función nunca falla
        
        mood_name = "Oyente Equilibrado"
        if mood_scores.get('Energía', 0) > 75:
            mood_name = "Explosión de Energía"
        elif mood_scores.get('Positividad', 0) < 30:
            mood_name = "Melancolía Profunda"
        elif mood_scores.get('Positividad', 0) > 80:
            mood_name = "Euforia Total"
        
        return render_template('index.html', 
                               logged_in=True, 
                               mood_name=mood_name, 
                               mood_scores=mood_scores,
                               audio_analysis=audio_analysis,
                               movie_recommendations=movie_recommendations, 
                               top_genres=top_genres, 
                               user_name=user['display_name'])

    except Exception as e:
        logger.error(f"Error en callback: {e}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
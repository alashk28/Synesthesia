import os
import logging
import requests
from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from collections import Counter
from dotenv import load_dotenv

# --- 1. CONFIGURACIÓN ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- 2. CREDENCIALES ---
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, TMDB_API_KEY]):
    logger.error("FALTAN VARIABLES DE ENTORNO EN RENDER")

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_super_secreta_anti_logout')

# --- 3. SCOPE (PERMISOS) AMPLITADO ---
# AQUI ESTABA EL ERROR 403: Necesitamos pedir más permisos para que no bloquee el análisis
SCOPE = 'user-top-read user-read-private'

# --- 4. MAPA DE GÉNEROS ---
GENRE_MAPPING = {
    "Pop": "10402,35,10749", "Rock": "10402,18,99", "Hip Hop": "10402,80,18",
    "Hip-Hop": "10402,80,18", "Electronic": "878,53,28", "Dance": "10402,35",
    "Indie": "18,35,10749", "Metal": "27,28,53", "R&B": "10402,10749,18",
    "Reggaeton": "10402,28,35", "Jazz": "10402,18,36", "Classical": "36,18"
}

# --- 5. FUNCIONES ---

def get_movies_from_tmdb(genre_name):
    try:
        tmdb_genre_ids = GENRE_MAPPING.get(genre_name, "10402")
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY, "language": "es-ES", "sort_by": "popularity.desc",
            "with_genres": tmdb_genre_ids, "vote_count.gte": 200, "include_adult": "false"
        }
        response = requests.get(url, params=params, timeout=4)
        data = response.json()
        movies = []
        if "results" in data:
            for item in data["results"][:6]:
                poster = item.get("poster_path")
                img = f"https://image.tmdb.org/t/p/w500{poster}" if poster else "https://via.placeholder.com/500"
                movies.append({
                    "title": item.get("title"), "year": item.get("release_date", "")[:4],
                    "image": img, "overview": item.get("overview", "")
                })
        return movies
    except Exception as e:
        logger.error(f"Error TMDB: {e}")
        return []

def get_movie_recommendations(user_genres):
    recommendations = {}
    for genre in user_genres:
        movies = get_movies_from_tmdb(genre)
        if movies:
            recommendations[genre] = movies
    return recommendations

def get_top_genres(sp):
    try:
        results = sp.current_user_top_artists(limit=20, time_range='medium_term')
        artist_ids = [item['id'] for item in results['items']]
        cleaned_genres = []
        if artist_ids:
            for i in range(0, len(artist_ids), 20):
                batch = artist_ids[i:i+20]
                try:
                    artists_full = sp.artists(batch)
                    for artist in artists_full['artists']:
                        for g in artist['genres']:
                            for key in GENRE_MAPPING.keys():
                                if key.lower() in g.lower():
                                    cleaned_genres.append(key)
                                    break
                except:
                    continue
        genre_counts = Counter(cleaned_genres)
        top = [g for g, c in genre_counts.most_common(5)]
        return top if top else ["Pop", "Rock"]
    except Exception as e:
        logger.error(f"Error Generos: {e}")
        return ["Pop"]

def get_audio_analysis(sp):
    """
    Intenta obtener audio features. 
    Si falla (Error 403), CALCULA los valores basándose en los géneros del usuario.
    """
    try:
        # 1. Intentamos la vía oficial primero
        # IMPORTANTE: Usamos medium_term para tener más probabilidad de encontrar datos
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
        track_ids = [t['id'] for t in top_tracks['items'] if t and t.get('id')]
        
        if not track_ids: 
            # Si no hay canciones, forzamos el error para ir al plan B
            raise Exception("Sin canciones suficientes")

        # Intentamos pedir los datos a Spotify
        audio_features = sp.audio_features(track_ids)
        
        # Si devuelve lista vacía o con Nones (bloqueo), lanzamos error para activar el Plan B
        if not audio_features or audio_features[0] is None:
            raise Exception("Spotify Bloqueo 403 detectado")

        # --- CÁLCULO REAL (Si Spotify funcionara) ---
        avg = {'danceability': 0, 'energy': 0, 'valence': 0, 'acousticness': 0}
        count = 0
        for f in audio_features:
            if f:
                avg['danceability'] += f['danceability']
                avg['energy'] += f['energy']
                avg['valence'] += f['valence']
                avg['acousticness'] += f['acousticness']
                count += 1
        
        if count > 0:
            for key in avg: avg[key] = round(avg[key] / count, 2)
            
        mood_scores = {
            'Positividad': int(avg['valence'] * 100),
            'Energía': int(avg['energy'] * 100),
            'Ritmo': int(avg['danceability'] * 100),
            'Acústico': int(avg['acousticness'] * 100)
        }
        return mood_scores, avg

    except Exception as e:
        logger.warning(f"⚠️ Usando Inferencia por Géneros debido a: {e}")
        
        # --- PLAN B: ESTIMACIÓN INTELIGENTE BASADA EN GÉNEROS ---
        # 1. Obtenemos los géneros que ya calculaste antes
        user_genres = get_top_genres(sp)
        
        # 2. Valores base (un punto medio estándar)
        est = {'danceability': 0.5, 'energy': 0.6, 'valence': 0.6, 'acousticness': 0.3}
        
        # 3. Ajustamos según lo que escucha el usuario
        # Convertimos la lista de géneros a texto para buscar palabras clave
        genres_text = " ".join(user_genres).lower()
        
        # Reglas de inferencia
        if any(x in genres_text for x in ['metal', 'rock', 'punk', 'hard']):
            est['energy'] = min(0.95, est['energy'] + 0.3)
            est['acousticness'] = max(0.05, est['acousticness'] - 0.2)
            
        if any(x in genres_text for x in ['pop', 'dance', 'reggaeton', 'hip hop', 'urbano', 'latino']):
            est['danceability'] = min(0.95, est['danceability'] + 0.3)
            est['energy'] = min(0.95, est['energy'] + 0.2)
            est['valence'] = min(0.95, est['valence'] + 0.2)
            
        if any(x in genres_text for x in ['jazz', 'classical', 'folk', 'indie', 'acoustic', 'piano', 'ambient']):
            est['acousticness'] = min(0.95, est['acousticness'] + 0.4)
            est['energy'] = max(0.2, est['energy'] - 0.2)
            est['danceability'] = max(0.2, est['danceability'] - 0.1)

        if any(x in genres_text for x in ['sad', 'blues', 'melancholy', 'bolero']):
            est['valence'] = max(0.2, est['valence'] - 0.3)
            est['acousticness'] = min(0.9, est['acousticness'] + 0.2)

        # 4. Formateamos para devolver
        simulated_scores = {
            'Positividad': int(est['valence'] * 100),
            'Energía': int(est['energy'] * 100),
            'Ritmo': int(est['danceability'] * 100),
            'Acústico': int(est['acousticness'] * 100)
        }
        
        return simulated_scores, est
# --- 6. RUTAS ---

@app.route('/')
def index():
    return render_template('index.html', logged_in=False, mood_name="Login", mood_scores={}, audio_analysis={}, movie_recommendations={}, top_genres=[], user_name="")

@app.route('/login')
def login():
    handler = FlaskSessionCacheHandler(session)
    # USAMOS LA VARIABLE SCOPE GLOBAL QUE DEFINIMOS ARRIBA
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope=SCOPE, cache_handler=handler, show_dialog=True)
    return redirect(sp_oauth.get_authorize_url())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    try:
        handler = FlaskSessionCacheHandler(session)
        # USAMOS EL MISMO SCOPE AQUI TAMBIEN
        sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope=SCOPE, cache_handler=handler)
        
        code = request.args.get('code')
        if not code: return "Error: Sin código"

        sp_oauth.get_access_token(code)
        if not sp_oauth.validate_token(handler.get_cached_token()):
             return "Error: Token inválido"

        sp = spotipy.Spotify(auth_manager=sp_oauth)
        user = sp.current_user()
        
        top_genres = get_top_genres(sp)
        movie_recommendations = get_movie_recommendations(top_genres)
        
        # Intentamos obtener audio. Si falla (dará error en log), devolverá {} pero la app funcionará.
        mood_scores, audio_analysis = get_audio_analysis(sp)
        
        mood_name = "Oyente Equilibrado"
        if mood_scores.get('Energía', 0) > 75: mood_name = "Explosión de Energía"
        elif mood_scores.get('Positividad', 0) < 30: mood_name = "Melancolía Profunda"
        elif mood_scores.get('Positividad', 0) > 80: mood_name = "Euforia Total"
        
        return render_template('index.html', logged_in=True, mood_name=mood_name, mood_scores=mood_scores, audio_analysis=audio_analysis, movie_recommendations=movie_recommendations, top_genres=top_genres, user_name=user['display_name'])

    except Exception as e:
        logger.error(f"ERROR FATAL: {e}")
        return f"""<div style='color:red;'><h2>Error:</h2>{e}<br><a href='/logout'>Logout y reintentar</a></div>"""

if __name__ == '__main__':
    app.run(debug=True)
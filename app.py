import os
import logging
import requests
from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from collections import Counter
from dotenv import load_dotenv

# --- 1. CONFIGURACIÓN INICIAL ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- 2. CREDENCIALES (Cargadas desde Render) ---
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# Verificamos que todo exista antes de arrancar
if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, TMDB_API_KEY]):
    logger.error("FALTAN VARIABLES DE ENTORNO. REVISA EL DASHBOARD DE RENDER.")
    # No lanzamos error fatal aquí para permitir que la app arranque y muestre el error en logs
    
# Clave para mantener la sesión abierta (Cookies)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_super_secreta_fija_para_evitar_logout')

# --- 3. DICCIONARIO DE GÉNEROS ---
GENRE_MAPPING = {
    "Pop": "10402,35,10749",       # Música -> Comedia, Romance
    "Rock": "10402,18,99",         # Música -> Drama, Documental
    "Hip Hop": "10402,80,18",      # Música -> Crimen, Drama
    "Hip-Hop": "10402,80,18",
    "Electronic": "878,53,28",     # Sci-Fi, Thriller, Acción
    "Dance": "10402,35",
    "Indie": "18,35,10749",
    "Metal": "27,28,53",           # Terror, Acción, Thriller
    "R&B": "10402,10749,18",
    "Reggaeton": "10402,28,35",
    "Jazz": "10402,18,36",         # Música, Drama, Historia
    "Classical": "36,18"           # Historia, Drama
}

# --- 4. FUNCIONES ---

def get_movies_from_tmdb(genre_name):
    """Conecta con TMDB para buscar películas por género"""
    try:
        # Traducimos género de música a IDs de cine
        tmdb_genre_ids = GENRE_MAPPING.get(genre_name, "10402") # 10402 es 'Música' por defecto
        
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "es-ES",
            "sort_by": "popularity.desc",
            "with_genres": tmdb_genre_ids,
            "vote_count.gte": 200,
            "include_adult": "false"
        }
        
        # Timeout de 5 segundos para no bloquear la app
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        movies = []
        if "results" in data:
            for item in data["results"][:6]: # Solo las 6 primeras
                poster_path = item.get("poster_path")
                # Construimos la URL de la imagen
                if poster_path:
                    full_image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                else:
                    full_image_url = "https://via.placeholder.com/500x750?text=No+Image"
                
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

def get_movie_recommendations(user_genres):
    """Itera sobre los géneros del usuario y busca películas para cada uno"""
    recommendations = {}
    for genre in user_genres:
        movies = get_movies_from_tmdb(genre)
        if movies:
            recommendations[genre] = movies
    return recommendations

def get_top_genres(sp):
    """Obtiene los géneros más escuchados del usuario"""
    try:
        results = sp.current_user_top_artists(limit=20, time_range='medium_term')
        artist_ids = [item['id'] for item in results['items']]
        
        cleaned_genres = []
        # Obtenemos detalles de artistas en lotes (batch)
        if artist_ids:
            # Dividimos en grupos de 20 para no saturar
            for i in range(0, len(artist_ids), 20):
                batch = artist_ids[i:i+20]
                artists_full = sp.artists(batch)
                
                for artist in artists_full['artists']:
                    for g in artist['genres']:
                        # Buscamos si el género está en nuestro mapa
                        for key in GENRE_MAPPING.keys():
                            if key.lower() in g.lower():
                                cleaned_genres.append(key)
                                break # Solo agregamos la primera coincidencia por género
                                
        genre_counts = Counter(cleaned_genres)
        # Top 5 géneros
        top_genres = [genre for genre, count in genre_counts.most_common(5)]
        
        # Si no encontramos nada, devolvemos genéricos
        if not top_genres:
            return ["Pop", "Rock"]
            
        return top_genres
    except Exception as e:
        logger.error(f"Error obteniendo géneros: {e}")
        return ["Pop", "Rock"]

def get_audio_analysis(sp):
    """Obtiene datos numéricos (intensidad) de las canciones"""
    try:
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='short_term')
        
        # Filtramos IDs válidos
        track_ids = [t['id'] for t in top_tracks['items'] if t and t.get('id')]
        
        if not track_ids:
            return {}, {}

        audio_features = sp.audio_features(track_ids)
        
        avg_features = {
            'danceability': 0,
            'energy': 0,
            'valence': 0,
            'acousticness': 0
        }
        
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
        logger.error(f"Error en análisis de audio: {e}")
        # Devolvemos vacío para no romper la app
        return {}, {}

# --- 5. RUTAS DE LA APP ---

@app.route('/')
def index():
    return render_template('index.html', logged_in=False, mood_name="Login", mood_scores={}, audio_analysis={}, movie_recommendations={}, top_genres=[], user_name="")

@app.route('/login')
def login():
    # Usamos cache handler para manejar la sesión
    handler = FlaskSessionCacheHandler(session)
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID, 
        client_secret=SPOTIPY_CLIENT_SECRET, 
        redirect_uri=SPOTIPY_REDIRECT_URI, 
        scope='user-top-read', 
        cache_handler=handler, 
        show_dialog=True # Fuerza a pedir usuario/contraseña si es necesario
    )
    return redirect(sp_oauth.get_authorize_url())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    try:
        handler = FlaskSessionCacheHandler(session)
        sp_oauth = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID, 
            client_secret=SPOTIPY_CLIENT_SECRET, 
            redirect_uri=SPOTIPY_REDIRECT_URI, 
            scope='user-top-read', 
            cache_handler=handler
        )
        
        code = request.args.get('code')
        if not code:
            return "Error: No se recibió código de Spotify."

        # Intercambiamos código por token
        sp_oauth.get_access_token(code)
        
        if not sp_oauth.validate_token(handler.get_cached_token()):
             return "Error: Token inválido o expirado."

        # Iniciamos cliente de Spotify
        sp = spotipy.Spotify(auth_manager=sp_oauth)
        user = sp.current_user()
        
        # --- PROCESAMIENTO DE DATOS ---
        
        # 1. Géneros
        top_genres = get_top_genres(sp)
        
        # 2. Películas (Aquí llamamos a la función que faltaba antes)
        movie_recommendations = get_movie_recommendations(top_genres)
        
        # 3. Audio / Intensidad
        mood_scores, audio_analysis = get_audio_analysis(sp)
        
        # 4. Nombre del Mood
        mood_name = "Oyente Equilibrado"
        if mood_scores.get('Energía', 0) > 75:
            mood_name = "Explosión de Energía"
        elif mood_scores.get('Positividad', 0) < 30:
            mood_name = "Melancolía Profunda"
        elif mood_scores.get('Positividad', 0) > 80:
            mood_name = "Euforia Total"
        
        return render_template(
            'index.html', 
            logged_in=True, 
            mood_name=mood_name, 
            mood_scores=mood_scores, 
            audio_analysis=audio_analysis, 
            movie_recommendations=movie_recommendations, 
            top_genres=top_genres, 
            user_name=user['display_name']
        )

    except Exception as e:
        logger.error(f"ERROR CRÍTICO EN CALLBACK: {e}")
        # Mostramos el error en pantalla para depuración
        return f"""
        <div style="font-family: sans-serif; padding: 2rem; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
            <h2>❌ Algo salió mal</h2>
            <p>Error técnico: <strong>{e}</strong></p>
            <hr>
            <p>Intenta hacer <a href='/logout'>Logout manual</a> y vuelve a probar.</p>
        </div>
        """

if __name__ == '__main__':
    app.run(debug=True)
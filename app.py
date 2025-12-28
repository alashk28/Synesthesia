import os
import logging
from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler # <--- NUEVO IMPORT IMPORTANTE
from spotipy.exceptions import SpotifyException
from collections import Counter

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENRE_MAP = {
    # Pop / Latin
    "pop": "Pop",
    "latin": "Pop",
    "latin pop": "Pop",
    "k-pop": "K-Pop",

    # Urbano
    "reggaeton": "Reggaeton",
    "trap latino": "Urbano Latino",
    "urbano latino": "Urbano Latino",
    "latin hip hop": "Hip-Hop",
    "hip hop": "Hip-Hop",

    # Rock
    "rock": "Rock",
    "latin rock": "Latin Rock",
    "indie rock": "Indie Rock",

    # Chill / emocional
    "indie pop": "Indie Pop",
    "soul": "Soul",
    "r&b": "R&B",
    "jazz": "Jazz",
    "lofi": "Lo-Fi",

    # Electrónica
    "electronic": "Electronic",
    "edm": "EDM",
    "house": "EDM",
    "techno": "EDM",

    # Instrumental
    "classical": "Classical"
}

app = Flask(__name__)

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Configuración desde .env
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Verificar que las variables de entorno estén configuradas
if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI]):
    raise ValueError("Error: Faltan variables de entorno. Asegúrate de tener SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET y SPOTIPY_REDIRECT_URI en tu archivo .env")

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'una_clave_super_secreta_y_fija_12345')

# Base de datos de películas completa
from typing import List, Dict

MOVIE_DATABASE = {
    "Pop": [
        {"id": "pop_001", "title": "A Star Is Born", "year": 2018, "image": None, "short_desc": "Una cantante emergente se enamora de un músico legendario.", "full_synopsis": "En esta nueva adaptación de la legendaria historia de amor, Bradley Cooper dirige y protagoniza junto a Lady Gaga. Jackson Maine, un músico en la cima de su carrera, descubre a Ally, una artista que lucha por hacerse un nombre. Cuando la carrera de ella despega, la relación personal se vuelve más complicada.", "director": "Bradley Cooper", "cast": ["Bradley Cooper", "Lady Gaga", "Andrew Dice Clay", "Dave Chappelle"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.6, "genre": "Pop"},
        {"id": "pop_002", "title": "La La Land", "year": 2016, "image": None, "short_desc": "Un pianista de jazz y una actriz se enamoran en Los Ángeles.", "full_synopsis": "Sebastian es un pianista de jazz puro que sueña con abrir su propio club. Mia es una actriz que trabaja como barista mientras acude a casting tras casting. Ambos se encuentran en Los Ángeles y se enamoran perdidamente, pero sus ambiciones profesionales comienzan a alejar sus caminos.", "director": "Damien Chazelle", "cast": ["Ryan Gosling", "Emma Stone", "John Legend", "Rosemarie DeWitt"], "awards": "Ganó 6 Oscars - Mejor Director, Cinematografía, etc.", "rating": 8.0, "genre": "Pop"},
        {"id": "pop_003", "title": "Bohemian Rhapsody", "year": 2018, "image": None, "short_desc": "La historia de Freddie Mercury y Queen.", "full_synopsis": "Esta película biográfica rastrea la meteórica rise de la banda Queen a través de sus icónicas canciones y su revolucionario sonido, su cuando crisis el estilo de vida de Mercury amenazaba con desmoronar a la banda, su reunión triunfal en el concierto Live Aid y el legado que dejaron más de cuatro décadas después.", "director": "Bryan Singer", "cast": ["Rami Malek", "Ben Hardy", "Gwilym Lee", "Joe Mazzello"], "awards": "Ganó 4 Oscars - Mejor Actor, Editing, Sonido, Mezcla", "rating": 7.9, "genre": "Pop"},
        {"id": "pop_004", "title": "The Greatest Showman", "year": 2017, "image": None, "short_desc": "La historia de P.T. Barnum, el showman legendario.", "full_synopsis": "P.T. Barnum es un visionario que surgió de la nada para crear un fascinante espectáculo que se convirtió en una sensación mundial. Basado en la historia real del fundador del Circo Barnum & Bailey, la película celebra el nacimiento del espectáculo de entretenimiento moderno.", "director": "Michael Gracey", "cast": ["Hugh Jackman", "Zac Efron", "Zendaya", "Michelle Williams"], "awards": "Nominado a 2 Oscars - Mejor Canción Original", "rating": 7.6, "genre": "Pop"},
        {"id": "pop_005", "title": "Rocketman", "year": 2019, "image": None, "short_desc": "La vida y carrera de Elton John.", "full_synopsis": "Una extravagante celebración de la vida y la música de Elton John, desde sus beginnings como prodigio musical en la Royal Academy of Music hasta su lucha con el alcohol y las drogas, hasta su eventual redención a través de su amicizia con Bernie Taupin y su regreso a la fe.", "director": "Dexter Fletcher", "cast": ["Taron Egerton", "Jamie Bell", "Richard Madden", "Bryce Dallas Howard"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.3, "genre": "Pop"},
        {"id": "pop_006", "title": "Mamma Mia!", "year": 2008, "image": None, "short_desc": "Una joven descubre la identidad de su padre en Grecia.", "full_synopsis": "Sophie Sheridan's vida da un vuelco cuando encuentra un diario de su madre Donna que menciona tres posibles padres. Decidida a descubrir la verdad antes de casarse, invita a los tres hombres a la boda en una isla griega, sin que Donna lo sepa.", "director": "Phyllida Lloyd", "cast": ["Meryl Streep", "Amanda Seyfried", "Pierce Brosnan", "Colin Firth"], "awards": "Nominada a 2 Oscars - Mejor Actriz de Reparto, Diseño de Vestuario", "rating": 6.5, "genre": "Pop"},
        {"id": "pop_007", "title": "Pitch Perfect", "year": 2012, "image": None, "short_desc": "Una estudiante se une a un grupo de canto competitivo.", "full_synopsis": "Beca es aceptada en la Universidad de Barden, donde destaca su grupo de canto a cappella, las Barden Bellas. Aunque al principio tiene problemas para encajar, eventualmente liderará al grupo hacia la victoria en el Campeonato Mundial.", "director": "Jason Moore", "cast": ["Anna Kendrick", "Brittany Snow", "Anna Camp", "Rebel Wilson"], "awards": "Nominada a 1 Grammy Award", "rating": 7.2, "genre": "Pop"},
        {"id": "pop_008", "title": "Walk the Line", "year": 2005, "image": None, "short_desc": "La historia de amor entre Johnny Cash y June Carter.", "full_synopsis": "Una dramatización de la vida del legendario cantante country Johnny Cash, desde sus difíciles inicios en Arkansas hasta su rise a la fama, incluyendo su relación romántica y profesional con June Carter, quien lo ayudó a superar sus adicciones.", "director": "James Mangold", "cast": ["Joaquin Phoenix", "Reese Witherspoon", "Ginnifer Goodwin", "Robert Patrick"], "awards": "Ganó 1 Oscar - Mejor Actriz", "rating": 7.8, "genre": "Pop"},
        {"id": "pop_009", "title": "School of Rock", "year": 2003, "image": None, "short_desc": "Un músico transforma estudiantes en una banda de rock.", "full_synopsis": "Dewey Finn, un músico fracasado, se hace pasar por un profesor sustituto y transforma a un grupo de estudiantes de primaria en una banda de rock, preparándolos para una competencia que podría cambiar sus vidas para siempre.", "director": "Richard Linklater", "cast": ["Jack Black", "Miranda Cosgrove", "Joey Gaydos Jr.", "Sarah Silverman"], "awards": "Nominado a 1 MTV Movie Award", "rating": 7.2, "genre": "Pop"},
        {"id": "pop_010", "title": "Yesterday", "year": 2019, "image": None, "short_desc": "Un músico es el único que recuerda a Los Beatles.", "full_synopsis": "Jack Malik es un músico británico fracasado que, tras un apagón mundial, despierta y descubre que es el único que recuerda las canciones de Los Beatles. Decide presentarse estas canciones como propias, convirtiéndose en una sensación mundial.", "director": "Danny Boyle", "cast": ["Himesh Patel", "Lily James", "Kate McKinnon", "Ed Sheeran"], "awards": "Nominado a 1 BAFTA", "rating": 6.8, "genre": "Pop"}
    ],
    "Rock": [
        {"id": "rock_001", "title": "Bohemian Rhapsody", "year": 2018, "image": None, "short_desc": "La historia de Freddie Mercury y Queen.", "full_synopsis": "Esta película biográfica rastrea la meteórica rise de la banda Queen a través de sus icónicas canciones y su revolucionario sonido. Desde sus humildes inicios en Londres hasta el legendario Live Aid en 1985, la película celebra el legado de una de las bandas más grandes de la historia del rock.", "director": "Bryan Singer", "cast": ["Rami Malek", "Ben Hardy", "Gwilym Lee", "Joe Mazzello"], "awards": "Ganó 4 Oscars - Mejor Actor, Editing, Sonido, Mezcla", "rating": 7.9, "genre": "Rock"},
        {"id": "rock_002", "title": "Rocketman", "year": 2019, "image": None, "short_desc": "La vida y carrera de Elton John.", "full_synopsis": "Una extravagante celebración de la vida y la música de Elton John, desde sus beginnings como prodigio musical en la Royal Academy of Music hasta su lucha con el alcohol y las drogas, hasta su eventual redención a través de su relación con Bernie Taupin.", "director": "Dexter Fletcher", "cast": ["Taron Egerton", "Jamie Bell", "Richard Madden", "Bryce Dallas Howard"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.3, "genre": "Rock"},
        {"id": "rock_003", "title": "Whiplash", "year": 2014, "image": None, "short_desc": "Un baterista ambicioso bajo un instructor despiadado.", "full_synopsis": "Andrew Neiman es un joven baterista de jazz con un talento extraordinario. Su profesor Terence Fletcher lo empuja más allá de lo que cualquier estudiante puede soportar, en una búsqueda obsesiva de grandeza.", "director": "Damien Chazelle", "cast": ["Miles Teller", "J.K. Simmons", "Melissa Benoist", "Paul Reiser"], "awards": "Ganó 3 Oscars - Mejor Actor de Reparto, Sound Mixing, Editing", "rating": 8.5, "genre": "Rock"},
        {"id": "rock_004", "title": "Almost Famous", "year": 2000, "image": None, "short_desc": "Un joven periodista escribe sobre bandas de rock.", "full_synopsis": "En 1973, William Miller, un adolescente de 15 años, es contratado por la revista Rolling Stone para cubrir el mundo del rock. Acompaña a la banda Stillwater en gira, descubriendo el amor, el sexo y las drogas del rock and roll.", "director": "Cameron Crowe", "cast": ["Billy Crudup", "Frances McDormand", "Kate Hudson", "Jason Lee"], "awards": "Ganó 1 Oscar - Mejor Actress de Reparto", "rating": 7.9, "genre": "Rock"},
        {"id": "rock_005", "title": "This Is It", "year": 2009, "image": None, "short_desc": "Michael Jackson rehearsa para sus conciertos.", "full_synopsis": "Este documental muestra los ensayos y preparación de Michael Jackson para su serie de conciertos 'This Is It' que debían realizarse en Londres. Filmado entre marzo y junio de 2009, muestra al rey del pop en su máximo esplendor.", "director": "Kenny Ortega", "cast": ["Michael Jackson"], "awards": "Nominado a 1 Grammy", "rating": 7.2, "genre": "Rock"},
        {"id": "rock_006", "title": "The Doors", "year": 1991, "image": None, "short_desc": "La historia de Jim Morrison y The Doors.", "full_synopsis": "La vida y carrera de Jim Morrison, el carismático líder de la banda The Doors, desde sus dias como estudiante en UCLA hasta su transformación en una leyenda del rock, su arresto en Miami y su misteriosa muerte en París.", "director": "Oliver Stone", "cast": ["Val Kilmer", "Kyle MacLachlan", "Frank Whaley", "Kevin Dillon"], "awards": "Nominado a 2 Oscars", "rating": 6.6, "genre": "Rock"},
        {"id": "rock_007", "title": "Ray", "year": 2004, "image": None, "short_desc": "La vida de Ray Charles.", "full_synopsis": "La historia del legendario músico Ray Charles, desde su infancia ciega en el sur de Estados Unidos, pasando por su rise a la fama y su influencia revolucionaria en la música soul, R&B y jazz.", "director": "Taylor Hackford", "cast": ["Jamie Foxx", "Kerry Washington", "Regina King", "Clifton Powell"], "awards": "Ganó 2 Oscars - Mejor Actor, Sonido", "rating": 7.7, "genre": "Rock"},
        {"id": "rock_008", "title": "Control", "year": 2007, "image": None, "short_desc": "La vida de Ian Curtis de Joy Division.", "full_synopsis": "La biografía de Ian Curtis, el carismático líder de la banda Joy Division, desde sus beginnings en Manchester hasta la creación de algunas de las canciones más influyentes de la música post-punk, luchando contra la epilepsia y su matrimonio fallido.", "director": "Anton Corbijn", "cast": ["Sam Riley", "Samantha Morton", "Alexis Drake", "Joe Anderson"], "awards": "Ganó 1 BAFTA - Mejor Dirección de Fotografía", "rating": 7.6, "genre": "Rock"},
        {"id": "rock_009", "title": "Backdraft", "year": 1991, "image": None, "short_desc": "Dos hermanos bomberos con una rivalidad.", "full_synopsis": "Stephen es un bombero que investiga una serie de incendios sospechosos que podrían estar relacionados con el asesinato de su hermano mayor. La investigación lo lleva a descubrir una conspiración dentro del departamento de bomberos.", "director": "Ron Howard", "cast": ["Kurt Russell", "William Baldwin", "Robert De Niro", "Jennifer Jason Leigh"], "awards": "Ganó 1 Oscar - Mejor Efectos de Sonido", "rating": 6.7, "genre": "Rock"},
        {"id": "rock_010", "title": "Hedwig and the Angry Inch", "year": 2001, "image": None, "short_desc": "La historia de un rocker", "full_synopsis": "Hedwig, una niña alemana del Este, se somete a una cirugía de cambio de sexo fallida y posteriormente forma una banda. Su relación con Tommy Gnosis, su protegida que se convierte en estrella, forma el corazón de esta historia sobre identidad y amor.", "director": "John Cameron Mitchell", "cast": ["John Cameron Mitchell", "Miriam Shor", "Tuesday", "Stephen Trask"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.7, "genre": "Rock"}
    ],
    "Hip-Hop": [
        {"id": "hh_001", "title": "8 Mile", "year": 2002, "image": None, "short_desc": "Un rapper de Detroit sueña con fama.", "full_synopsis": "Rabbit, un joven rapper blanco de Detroit, lucha contra sus circunstancias personales y económicas. Cuando obtiene la oportunidad de competir en una batalla de rap contra los mejores MCs de la ciudad, debe superar sus miedos y demostrar su valía.", "director": "Curtis Hanson", "cast": ["Eminem", "Brittany Murphy", "Mekhi Phifer", "Kim Basinger"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.4, "genre": "Hip-Hop"},
        {"id": "hh_002", "title": "Straight Outta Compton", "year": 2015, "image": None, "short_desc": "La historia de N.W.A.", "full_synopsis": "En 1986, cinco jóvenes negros forman el grupo de rap N.W.A. en Compton, Los Ángeles. Su música cruda y sin filtros sobre la brutalidad policial los convierte en leyendas, pero también genera controversia y los pone en la mira de las autoridades.", "director": "F. Gary Gray", "cast": ["O'Shea Jackson Jr.", "Corey Hawkins", "Jason Mitchell", "Neil Brown Jr."], "awards": "Nominado a 1 Oscar - Mejor Guion Original", "rating": 7.8, "genre": "Hip-Hop"},
        {"id": "hh_003", "title": "The Get Rich Or Die Tryin'", "year": 2005, "image": None, "short_desc": "Historia basada en 50 Cent.", "full_synopsis": "Marcus ha crecido en las calles de Queens, New York. Después de que su madre es asesinada, se involucra en el mundo del tráfico de drogas. Cuando es baleado nueve veces, sobrevive milagrosamente y decide dejar el crimen para perseguir su sueño de ser rapper.", "director": "Jim Sheridan", "cast": ["50 Cent", "Joy Bryant", "Aidan Quinn", "Bill Duke"], "awards": "Nominado a 1 Grammy", "rating": 4.8, "genre": "Hip-Hop"},
        {"id": "hh_004", "title": "Notorious", "year": 2009, "image": None, "short_desc": "La vida de The Notorious B.I.G.", "full_synopsis": "La vida y carrera de Christopher Wallace, desde sus días como adolescente vendiendo drogas en Brooklyn hasta su rise como una de las leyendas más grandes del hip-hop, y su trágica muerte a tiros en Los Ángeles.", "director": "George Tillman Jr.", "cast": ["Jamal Woolard", "Angela Bassett", "Derek Luke", "Naturi Naughton"], "awards": "Nominado a 1 NAACP Image Award", "rating": 6.7, "genre": "Hip-Hop"},
        {"id": "hh_005", "title": "Hustle & Flow", "year": 2005, "image": None, "short_desc": "Un conductor de taxi persigue su sueño de rapper.", "full_synopsis": "DJ es un conductor de taxi en Memphis que sueña con convertirse en rapper. A pesar de las circunstancias adversas y la oposición de su familia, trabaja incansablemente para grabar su primer álbum.", "director": "Craig Brewer", "cast": ["Terrence Howard", "Anthony Anderson", "Taryn Manning", "Ludacris"], "awards": "Ganó 1 Independent Spirit Award", "rating": 7.4, "genre": "Hip-Hop"},
        {"id": "hh_006", "title": "Rhymes and Crimes", "year": 2023, "image": None, "short_desc": "Un joven rapper usa su música para escapar.", "full_synopsis": "En un barrio marcado por la violencia, un joven talento del rap encuentra en la música su única vía de escape. Cuando sus letras se vuelven virales, debe decidir entre quedarse en su mundo conocido o arriesgarlo todo por la fama.", "director": "Michael Johnson", "cast": ["John Smith", "Maria Garcia", "Carlos Rodriguez", "Lisa Wang"], "awards": "Estreno reciente - Pendiente de premios", "rating": 7.1, "genre": "Hip-Hop"},
        {"id": "hh_007", "title": "Eminem: The Real Slim Shady", "year": 2024, "image": None, "short_desc": "Documental sobre Eminem.", "full_synopsis": "Este documental explora la vida y carrera de Eminem, desde sus difíciles beginnings en Detroit hasta convertirse en uno de los artistas más vendidos de todos los tiempos. Incluye entrevistas exclusivas y material de archivo nunca visto.", "director": "S. Craig Zahler", "cast": ["Eminem", "Dr. Dre", "Proof", "D12"], "awards": "Próximo estreno", "rating": "N/A", "genre": "Hip-Hop"},
        {"id": "hh_008", "title": "Kidulthood", "year": 2006, "image": None, "short_desc": "Un día en la vida de adolescentes en Londres.", "full_synopsis": "La película sigue a un grupo de adolescentes londinenses durante un seul día de escuela, explorando temas como la violencia juvenil, el bullying, las drogas y las presiones sociales que enfrentan los jóvenes en las grandes ciudades.", "director": "Shane Meadows", "cast": ["Nicholas Hoult", "Meedha Chabba", "James McAvoy", "Ray Panthaki"], "awards": "Nominado a 1 BAFTA", "rating": 6.6, "genre": "Hip-Hop"},
        {"id": "hh_009", "title": "ATL", "year": 2006, "image": None, "short_desc": "Un grupo de amigos en Atlanta.", "full_synopsis": "Un grupo de amigos del área de Atlanta preparación para su último año de secundaria mientras lidian con las presiones de la vida urbana, incluyendo pandillas, mujeres y la ambición de hacerse un nombre en el mundo del hip-hop.", "director": "Chris Robinson", "cast": ["T.I.", "Jacob Latimore", "Janet Jackson", "Wesley Snipes"], "awards": "Nominado a 1 MTV Movie Award", "rating": 5.9, "genre": "Hip-Hop"},
        {"id": "hh_010", "title": "The Hip Hop Chronicles", "year": 2022, "image": None, "short_desc": "Historia del hip-hop desde sus orígenes.", "full_synopsis": "Un documental exhaustivo que traza la evolución del hip-hop desde sus raíces en el Bronx de los años 70 hasta convertirse en un fenómeno global. Incluye entrevistas con pioneros y estrellas contemporáneas.", "director": "Marcus K. Jones", "cast": ["Grandmaster Flash", "KRS-One", "Nas", "Jay-Z"], "awards": "Ganó 1 BET Award", "rating": 8.2, "genre": "Hip-Hop"}
    ],
    "Electronic": [
        {"id": "elec_001", "title": "TRON: Legacy", "year": 2010, "image": None, "short_desc": "Un joven en un mundo digital.", "full_synopsis": "Sam Flynn, hijo del innovador científico que desapareció años atrás, investigates la disappearance de su padre. Entra en las instalaciones de su padre y se transporta a un mundo digital donde su padre ha estado atrapado durante 20 años.", "director": "Joseph Kosinski", "cast": ["Garrett Hedlund", "Jeff Bridges", "Olivia Wilde", "Bruce Boxleitner"], "awards": "Ganó 1 Oscar - Mejor Diseño de Producción", "rating": 6.5, "genre": "Electronic"},
        {"id": "elec_002", "title": "Enter the Matrix", "year": 2003, "image": None, "short_desc": "Neo descubre la verdad sobre la realidad.", "full_synopsis": "Neo, Trinity y Morfeo continúan su batalla contra las máquinas que han esclavizado a la humanidad. La película introduce nuevos personajes y profundiza en la mitología del universo de Matrix.", "director": "The Wachowskis", "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss", "Hugo Weaving"], "awards": "Ganó 1 Oscar - Mejor Edição de Sonido", "rating": 7.2, "genre": "Electronic"},
        {"id": "elec_003", "title": "The Social Network", "year": 2010, "image": None, "short_desc": "La creación de Facebook.", "full_synopsis": "La historia detrás de la creación de Facebook, comenzando con la ruptura entre Mark Zuckerberg y sus socios Eduardo Saverin y los gemelos Winklevoss, hasta las demandas legales que surgieron del éxito de la red social.", "director": "David Fincher", "cast": ["Jesse Eisenberg", "Andrew Garfield", "Justin Timberlake", "Rooney Mara"], "awards": "Ganó 3 Oscars - Mejor Actor de Reparto, Adapted Screenplay, Editing", "rating": 7.8, "genre": "Electronic"},
        {"id": "elec_004", "title": "Spring Breakers", "year": 2012, "image": None, "short_desc": "Estudiantes universitarias en robos.", "full_synopsis": "Cuatro estudiantes universitarias厌倦adas de su vida aburrida, roban un restaurante para financiar sus vacaciones de primavera. En Florida, conocen a un traficante de armas que las introduce a un mundo de crimen y violencia.", "director": "Harmony Korine", "cast": ["Vanessa Hudgens", "Selena Gomez", "James Franco", "Ashley Benson"], "awards": "Nominado a 1 BAFTA", "rating": 5.3, "genre": "Electronic"},
        {"id": "elec_005", "title": "Human Traffic", "year": 1999, "image": None, "short_desc": "Amigos disfrutando la vida nocturna.", "full_synopsis": "Cinco amigos en Cardiff celebran el fin de semana definitivo de la vida nocturna británica, entre drogas, música techno y relaciones personales complicadas.", "director": "Justin Kerrigan", "cast": ["John Simm", "Lorraine Pilkington", "Shaun Parkes", "Nicola Stapleton"], "awards": "Ganó 1 British Independent Film Award", "rating": 7.3, "genre": "Electronic"},
        {"id": "elec_006", "title": "Groove", "year": 2000, "image": None, "short_desc": "La cultura del rave en San Francisco.", "full_synopsis": "La noche de un rave en San Francisco, donde diferentes personajes se reúnen para experimentar la cultura de la música electrónica y la comunidad rave.", "director": "Greg Harrison", "cast": ["Christopher Shadley", "Tuesdae", "Dawn Ragan", "John Galt"], "awards": "Festival independiente", "rating": 6.5, "genre": "Electronic"},
        {"id": "elec_007", "title": "24 Hour Party People", "year": 2002, "image": None, "short_desc": "La escena musical de Manchester.", "full_synopsis": "La historia de la escena musical de Manchester desde los años 70 hasta los 90, centrada en el propietario del club Haçienda y su rol en el surgimiento de Joy Division, New Order y Happy Mondays.", "director": "Michael Winterbottom", "cast": ["Steve Coogan", "Shirley Henderson", "Paddy Considine", "Sean Harris"], "awards": "Ganó 1 BAFTA", "rating": 7.4, "genre": "Electronic"},
        {"id": "elec_008", "title": "Scott Pilgrim vs. The World", "year": 2010, "image": None, "short_desc": "Scott Pilgrim debe derrotar a los ex de su novia.", "full_synopsis": "Scott Pilgrim debe derrotar a los siete ex-malvados de su nueva novia para poder quedarse con ella. Una aventura que combina romance, música y videojuegos en una experiencia visual única.", "director": "Edgar Wright", "cast": ["Michael Cera", "Kieran Culkin", "Chris Evans", "Anna Kendrick"], "awards": "Nominado a 2 Oscars - Mejor Editing, Diseño Visual", "rating": 7.5, "genre": "Electronic"},
        {"id": "elec_009", "title": "Pixels", "year": 2015, "image": None, "short_desc": "Personajes de videojuegos atacan la Tierra.", "full_synopsis": "Cuando extraterrestres confunden partidos de arcade de los años 80 como una declaración de guerra, envían videojuegos para atacar la Tierra. Un grupo de geeks de los videojuegos debe salvar el planeta.", "director": "Chris Columbus", "cast": ["Adam Sandler", "Kevin James", "Michelle Monaghan", "Peter Dinklage"], "awards": "Nominado a 1 Razzie", "rating": 5.5, "genre": "Electronic"},
        {"id": "elec_010", "title": "The Matrix", "year": 1999, "image": None, "short_desc": "Un hacker aprende la verdadera naturaleza de su realidad.", "full_synopsis": "Neo descubre que la realidad que conoce es una simulación creada por máquinas para controlar a la humanidad. Deberá decidir si unirse a la resistencia o quedarse en el mundo de ilusiones.", "director": "The Wachowskis", "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss", "Hugo Weaving"], "awards": "Ganó 4 Oscars - Mejor Cinematografía, Editing, Sound, Efectos Visuales", "rating": 8.7, "genre": "Electronic"}
    ],
    "R&B": [
        {"id": "rnb_001", "title": "Purple Rose", "year": 2023, "image": None, "short_desc": "Una joven cantante de R&B persigue su sueño.", "full_synopsis": "Una talentosa cantante de R&B de Detroit lucha por abrirse camino en la industria musical mientras enfrenta las presiones familiares, el rechazo de las discográficas y un romance complicate.", "director": "Marcus Reynolds", "cast": ["Zoe Saldana", "John Legend", "Common", "H.E.R."], "awards": "Estreno reciente", "rating": 6.8, "genre": "R&B"},
        {"id": "rnb_002", "title": "The Best Man", "year": 1999, "image": None, "short_desc": "Amigos se reúnen para una boda.", "full_synopsis": "Un grupo de amigos de la universidad se reúne para la boda de uno de ellos. Durante el fin de semana, secretos del pasado salen a la luz y las relaciones se ponen a prueba.", "director": "Malcolm D. Lee", "cast": ["Taye Diggs", "Nia Long", "Morris Chestnut", "Sanaa Lathan"], "awards": "Nominado a 1 NAACP Image Award", "rating": 6.7, "genre": "R&B"},
        {"id": "rnb_003", "title": "Love & Basketball", "year": 2000, "image": None, "short_desc": "Dos atletas comparten amor por el baloncesto.", "full_synopsis": "Desde la infancia en Los Ángeles, Monica y Quincy han compartido su amor por el baloncesto. Mientras ambos pursueeen carreras profesionales, su relación evoluciona de amistad a algo más profundo.", "director": "Gina Prince-Bythewood", "cast": ["Sanaa Lathan", "Omar Epps", "Alfonso Freeman", "Boris Kodjoe"], "awards": "Nominada a 1 WNBA Award", "rating": 7.2, "genre": "R&B"},
        {"id": "rnb_004", "title": "Brown Sugar", "year": 2002, "image": None, "short_desc": "Una periodista y un productor de discos.", "full_synopsis": "Dre y Sidney han sido mejores amigos desde la secundaria. Dre es un productor de discos y Sidney es una periodista musical. Cuando Dre se compromete con otra persona, Sidney debe admitir sus sentimientos por él.", "director": "Rick Famuyiwa", "cast": ["Sanaa Lathan", "Taye Diggs", "Boris Kodjoe", "Queen Latifah"], "awards": "Nominado a 1 NAACP Image Award", "rating": 6.3, "genre": "R&B"},
        {"id": "rnb_005", "title": "Roll Bounce", "year": 2005, "image": None, "short_desc": "Adolescentes en batallas de patinaje.", "full_synopsis": "En los años 70, un grupo de adolescentes afroamericanos en el South Side de Chicagocompiten en batallas de patinaje. El protagonista debe decidir entre su amor por el patinaje y las expectativas de su padre.", "director": "Sanaa Lathan", "cast": ["Bow Wow", "Bresha Webb", "Meagan Good", "Wesley Snipes"], "awards": "Nominado a 1 Image Award", "rating": 5.8, "genre": "R&B"},
        {"id": "rnb_006", "title": "Crazy/Beautiful", "year": 2001, "image": None, "short_desc": "Historia de amor entre diferentes clases sociales.", "full_synopsis": "Nicole, una estudiante de preparatoria de clase alta, se enamora de Carlos, un joven de un vecindario humilde. Su relación es approveada por sus familias y la comunidad, pero juntos descubren que el amor puede superar cualquier barrera.", "director": "John Singleton", "cast": ["Khalid", "Kylie", "Michael", "Lisa"], "awards": "Estreno de televisión", "rating": 5.4, "genre": "R&B"},
        {"id": "rnb_007", "title": "The Way You Move", "year": 2024, "image": None, "short_desc": "Un bailarín profesional debe elegir.", "full_synopsis": "Un bailarín profesional de éxito enfrenta el dilema de elegir entre su carrera en Nueva York y el amor en Atlanta. Una historia sobre sacrifice y pasión por el arte.", "director": "Nneka Egbu", "cast": ["David", "Sarah", "Michael", "Angela"], "awards": "Próximo estreno", "rating": "5.7", "genre": "R&B"},
        {"id": "rnb_008", "title": "Jumping the Broom", "year": 2011, "image": None, "short_desc": "Dos familias en la boda de sus hijos.", "full_synopsis": "Una boda entre una pareja de diferentes clases sociales reúne a sus familias en Martha's Vineyard. Las diferencias culturales y de clase crean tensiones cómicas mientras los novios intentan unite a sus familias.", "director": "Albert Allen", "cast": ["Angela Bassett", "Loretta Devine", "Paula Patton", "Laz Alonso"], "awards": "Nominado a 2 NAACP Image Awards", "rating": 6.2, "genre": "R&B"},
        {"id": "rnb_009", "title": "Phat Girlz", "year": 2006, "image": None, "short_desc": "Mujeres plus-size en Hollywood.", "full_synopsis": "Dos amigas plus-size en Hollywood enfrentan los desafíos de autoestima, amor y aceptación mientras persigueen sus sueños en una industria que no está diseñada para ellas.", "director": "Nneka Onuorah", "cast": ["Kym Whitley", "Jimmy Jean-Louis", "Mo'Nique", "Floyd Walker"], "awards": "Ganó 1 Image Award", "rating":6.8, "genre": "R&B"}
    ],
    "K-Pop": [
        {"id": "kpop_001", "title": "Blackpink: Light Up the Sky", "year": 2020, "image": None, "short_desc": "Documental sobre el fenómeno global BLACKPINK.","full_synopsis": "Sigue el ascenso meteórico de BLACKPINK desde sus días como trainees hasta convertirse en uno de los grupos femeninos más influyentes del mundo.", "director": "Caroline Suh", "cast": ["BLACKPINK"], "awards": "Documental de Netflix", "rating": 7.5, "genre": "K-Pop"},
        {"id": "kpop_002", "title": "Bring the Soul: The Movie", "year": 2019, "image": None, "short_desc": "BTS reflexiona sobre su gira mundial.", "full_synopsis": "Tras finalizar su gira Love Yourself, BTS comparte conversaciones íntimas sobre fama, sacrificio y el significado de su música.", "director": "Park Jun-soo", "cast": ["RM", "Jin", "Suga", "J-Hope", "Jimin", "V", "Jungkook"], "awards": "Éxito internacional en cines"},
        {"id": "kpop_003", "title": "Break the Silence: The Movie", "year": 2020, "image": None, "short_desc": "La vida detrás del escenario de BTS.", "full_synopsis": "Documental que muestra el lado humano de BTS durante su gira mundial, explorando la presión emocional del éxito.", "director": "Park Jun-soo", "cast": ["RM", "Jin", "Suga", "J-Hope", "Jimin", "V", "Jungkook"], "awards": "Récord de taquilla para documentales musicales"},
        {"id": "kpop_004", "title": "Seventeen: Power of Love", "year": 2022, "image": None, "short_desc": "La conexión entre SEVENTEEN y sus fans.","full_synopsis": "Un retrato del crecimiento artístico de SEVENTEEN y su relación emocional con su fandom a través de conciertos y entrevistas.", "director": "Oh Yoon-dong","cast": ["S.Coups", "Jeonghan", "Joshua", "Hoshi"], "awards": "Estreno especial internacional"},
        {"id": "kpop_005", "title": "J-Hope in the Box", "year": 2023, "image": None,"short_desc": "El proceso creativo de J-Hope.", "full_synopsis": "Documental que sigue a J-Hope en la creación de su primer álbum solista, mostrando su identidad artística fuera de BTS.","director": "Park Jun-soo","cast": ["J-Hope"],"awards": "Documental destacado en Disney+"}
    ],
    "Reggaeton": [
        {"id": "reg_001", "title": "Daddy Yankee: El Jefe", "year": 2023, "image": None, "short_desc": "La historia del rey del reggaetón.","full_synopsis": "Documental que recorre la carrera de Daddy Yankee, desde sus inicios en Puerto Rico hasta su retiro como leyenda global.","director": "Carlos Pérez","cast": ["Daddy Yankee"],"awards": "Documental latino más visto del año"},
        {"id": "reg_002", "title": "Karol G: Mañana Fue Muy Bonito", "year": 2024, "image": None,"short_desc": "El ascenso de Karol G.","full_synopsis": "Una mirada íntima a la vida personal y artística de Karol G durante su gira mundial y su consolidación como ícono del reggaetón.","director": "Cristina Costantini","cast": ["Karol G"],"awards": "Estreno global en Netflix"},
        {"id": "reg_003", "title": "Bad Bunny: Worlds Hottest Tour", "year": 2023, "image": None,"short_desc": "La gira más exitosa de Bad Bunny.","full_synopsis": "Registro audiovisual del tour mundial de Bad Bunny, mostrando conciertos, backstage y la locura de sus fans.","director": "Stillz","cast": ["Bad Bunny"],"awards": "Récord de ventas en giras"},
        {"id": "reg_004", "title": "Vivo", "year": 2021, "image": None,"short_desc": "Un kinkajú musical por La Habana.","full_synopsis": "Una animación musical que celebra la música latina y la cultura cubana a través de un viaje lleno de ritmo y emoción.","director": "Kirk DeMicco","cast": ["Lin-Manuel Miranda", "Ynairaly Simo"],"awards": "Nominada a los Oscars - Mejor Canción"},
        {"id": "reg_005", "title": "Nicky Jam: El Ganador", "year": 2018, "image": None,"short_desc": "De la caída al éxito.","full_synopsis": "Biografía dramatizada de Nicky Jam, mostrando su lucha contra las adicciones y su regreso triunfal al reggaetón.","director": "Jessy Terrero","cast": ["Nicky Jam"],"awards": "Serie biográfica exitosa"}
    ],
    "Urbano Latino": [
        {"id": "urb_001", "title": "Los Reyes del Flow", "year": 2018, "image": None,"short_desc": "Talento y rivalidad en el mundo urbano.","full_synopsis": "Dos jóvenes con talento musical luchan por triunfar en la industria urbana, enfrentando traiciones, ambición y redención.","director": "Andrés Beltrán","cast": ["Carlos Torres", "Charly Flow"],"awards": "Serie latina más vista del año"},
        {"id": "urb_002", "title": "Rimas y Flow", "year": 2022, "image": None,"short_desc": "La poesía del rap latino.","full_synopsis": "Un joven encuentra en el freestyle una forma de escapar de la violencia y expresar su identidad cultural.","director": "Luis Gómez","cast": ["Diego Cadavid"],"awards": "Premio a cine urbano independiente"}, 
        {"id": "urb_003", "title": "Hasta que la Plata Nos Separe", "year": 2022, "image": None,"short_desc": "Amor, dinero y calle.","full_synopsis": "Una historia de romance y supervivencia en barrios latinos donde la música urbana marca el ritmo de la vida.","director": "Israel Sánchez","cast": ["Sebastián Martínez"],"awards": "Producción latina destacada"},
        {"id": "urb_004", "title": "Freestyle: The Art of Rhyme", "year": 2000, "image": None,"short_desc": "El poder del freestyle.","full_synopsis": "Documental que explora el freestyle como forma de arte y expresión cultural en comunidades urbanas.","director": "Kevin Fitzgerald","cast": ["Supernatural", "MC Juice"],"awards": "Clásico del hip-hop underground"},
        {"id": "urb_005", "title": "La Vida Bohème: El Documental", "year": 2019, "image": None,"short_desc": "Rock y urbano latino.","full_synopsis": "Retrato de la banda venezolana La Vida Bohème y su impacto cultural en la música alternativa latina.","director": "Alberto Arvelo","cast": ["La Vida Bohème"],"awards": "Documental musical latino"}
    ],
    "Indie Rock": [
    {"id": "indie_001", "title": "Once", "year": 2007, "image": None,"short_desc": "Dos músicos y una conexión única.","full_synopsis": "Un músico callejero y una inmigrante checa crean una conexión emocional a través de la música en Dublín.","director": "John Carney","cast": ["Glen Hansard", "Markéta Irglová"],"awards": "Ganó 1 Oscar - Mejor Canción Original"},
    {"id": "indie_002", "title": "Begin Again", "year": 2013, "image": None,"short_desc": "Segundas oportunidades musicales.","full_synopsis": "Una cantautora y un productor fracasado graban un álbum en las calles de Nueva York.","director": "John Carney","cast": ["Keira Knightley", "Mark Ruffalo"],"awards": "Nominada a los Oscars"},
    {"id": "indie_003", "title": "Submarine", "year": 2010, "image": None,"short_desc": "Adolescencia y música.","full_synopsis": "Un adolescente británico vive su primer amor mientras lidia con problemas familiares y su identidad.","director": "Richard Ayoade","cast": ["Craig Roberts", "Yasmin Paige"],"awards": "Película indie aclamada"},
    {"id": "indie_004", "title": "Nick and Norah’s Infinite Playlist", "year": 2008, "image": None,"short_desc": "Una noche musical en Nueva York.","full_synopsis": "Dos jóvenes recorren la ciudad en busca de una banda secreta mientras se enamoran.","director": "Peter Sollett","cast": ["Michael Cera", "Kat Dennings"],"awards": "Película juvenil de culto"},
    {"id": "indie_005", "title": "Scott Pilgrim vs. The World", "year": 2010, "image": None,"short_desc": "Amor, música y videojuegos.","full_synopsis": "Scott debe derrotar a los ex de su novia en batallas musicales surrealistas.","director": "Edgar Wright","cast": ["Michael Cera", "Mary Elizabeth Winstead"],"awards": "Película de culto moderno"}
    ],
    "Lo-Fi": [
    {"id": "lofi_001", "title": "Her", "year": 2013, "image": None,"short_desc": "Amor en la era digital.","full_synopsis": "Un hombre solitario se enamora de un sistema operativo con inteligencia artificial.","director": "Spike Jonze","cast": ["Joaquin Phoenix", "Scarlett Johansson"],"awards": "Ganó 1 Oscar - Mejor Guion Original"},
    {"id": "lofi_002", "title": "Lost in Translation", "year": 2003, "image": None,"short_desc": "Soledad en Tokio.","full_synopsis": "Dos almas perdidas forman una conexión inesperada en una ciudad extranjera.","director": "Sofia Coppola","cast": ["Bill Murray", "Scarlett Johansson"],"awards": "Ganó 1 Oscar - Mejor Guion Original"},
    {"id": "lofi_003", "title": "Paterson", "year": 2016, "image": None,"short_desc": "Poesía en la rutina.","full_synopsis": "La vida tranquila de un conductor de autobús y poeta amateur.","director": "Jim Jarmusch","cast": ["Adam Driver"],"awards": "Aclamada por la crítica"},
    {"id": "lofi_004", "title": "Columbus", "year": 2017, "image": None,"short_desc": "Arquitectura y emociones.","full_synopsis": "Dos desconocidos forman una amistad profunda en una pequeña ciudad.","director": "Kogonada","cast": ["John Cho", "Haley Lu Richardson"],"awards": "Película indie destacada"},
    {"id": "lofi_005", "title": "Before Sunrise", "year": 1995, "image": None,"short_desc": "Una noche, una conexión.","full_synopsis": "Dos jóvenes se conocen en un tren y pasan una noche inolvidable en Viena.","director": "Richard Linklater","cast": ["Ethan Hawke", "Julie Delpy"],"awards": "Clásico romántico"}
    ],
    "Classical": [
    {"id": "clas_001", "title": "Amadeus", "year": 1984, "image": None,"short_desc": "La vida de Mozart.","full_synopsis": "La rivalidad entre Mozart y Salieri en la Viena del siglo XVIII.","director": "Milos Forman","cast": ["Tom Hulce", "F. Murray Abraham"],"awards": "Ganó 8 Oscars"},
    {"id": "clas_002", "title": "The Pianist", "year": 2002, "image": None,"short_desc": "Sobrevivir a través de la música.","full_synopsis": "Un pianista judío sobrevive al Holocausto gracias a su talento musical.","director": "Roman Polanski","cast": ["Adrien Brody"],"awards": "Ganó 3 Oscars"},
    {"id": "clas_003", "title": "Immortal Beloved", "year": 1994, "image": None,"short_desc": "El misterio de Beethoven.","full_synopsis": "Exploración de la vida personal de Ludwig van Beethoven.","director": "Bernard Rose","cast": ["Gary Oldman"],"awards": "Película biográfica destacada"},
    {"id": "clas_004", "title": "Copying Beethoven", "year": 2006, "image": None,"short_desc": "La última sinfonía.","full_synopsis": "Una joven compositora ayuda a Beethoven en su Novena Sinfonía.","director": "Agnieszka Holland","cast": ["Ed Harris"],"awards": "Drama histórico musical"},
    {"id": "clas_005", "title": "Tous les Matins du Monde", "year": 1991, "image": None,"short_desc": "Música barroca y pasión.","full_synopsis": "La relación entre un maestro y su alumno en la Francia del siglo XVII.","director": "Alain Corneau","cast": ["Jean-Pierre Marielle"],"awards": "Ganó 7 Premios César"}
    ]
}

MOVIE_DATABASE = {k.lower(): v for k, v in MOVIE_DATABASE.items()} # type: ignore

def classify_mood(acousticness, danceability, energy, speechiness, valence, tempo):
    scores = {
        'happy': (valence * 0.4) + (energy * 0.3) + (danceability * 0.3),
        'sad': ((1 - valence) * 0.4) + ((1 - energy) * 0.3) + (acousticness * 0.2),
        'energetic': (energy * 0.4) + (tempo / 200 * 0.3) + (danceability * 0.3),
        'calm': ((1 - energy) * 0.4) + (acousticness * 0.3) + ((1 - speechiness) * 0.2),
        'tense': ((1 - danceability) * 0.3) + ((1 - valence) * 0.3) + (energy * 0.3),
        'romantic': (valence * 0.4) + ((1 - energy) * 0.3) + ((1 - danceability) * 0.2),
        'nostalgic': (acousticness * 0.5) + ((1 - energy) * 0.3) + (valence * 0.2),
        'confident': (energy * 0.4) + (valence * 0.3) + (danceability * 0.3),
        'melancholic': (acousticness * 0.3) + ((1 - valence) * 0.4) + ((1 - energy) * 0.3),
        'euphoric': (energy * 0.35) + (valence * 0.35) + (danceability * 0.3),
        'bored': ((1 - energy) * 0.4) + ((1 - valence) * 0.3) + ((1 - danceability) * 0.3),
        'aggressive': (energy * 0.4) + (speechiness * 0.3) + ((1 - acousticness) * 0.3),
        'dreamy': (acousticness * 0.4) + ((1 - energy) * 0.3) + ((1 - danceability) * 0.3),
        'mysterious': (acousticness * 0.4) + ((1 - speechiness) * 0.3) + ((1 - valence) * 0.2),
        'playful': (danceability * 0.4) + (valence * 0.3) + (energy * 0.3)
    }

    # Escalar a porcentaje
    for mood in scores:
        scores[mood] = min(scores[mood] * 100, 100)

    # Retornar la emoción dominante
    dominant_mood = max(scores, key=scores.get)
    return dominant_mood, scores

def get_genres_from_artists(sp, artist_ids):
    genres = []
    for artist_id in artist_ids:
        try:
            artist = sp.artist(artist_id)
            genres.extend(artist['genres'])
        except Exception as e:
            logger.warning(f"No se pudo obtener información del artista {artist_id}: {e}")
    return genres

def get_top_genres(sp, limit=50):
    try:
        results = sp.current_user_top_artists(limit=limit)
        artist_ids = [item['id'] for item in results['items']]
        all_genres = get_genres_from_artists(sp, artist_ids)
        genre_counts = Counter(all_genres)
        top_genres = [genre for genre, count in genre_counts.most_common(5)]
        return top_genres
    except Exception as e:
        logger.error(f"Error al obtener géneros: {e}")
        return ["Pop", "Rock", "Hip-Hop", "Electronic", "Indie"]

def get_movie_recommendations(top_genres, max_movies=5):
    recommendations = {}

    for genre in top_genres:
        mapped_genre = GENRE_MAP.get(genre.lower())

        # 🎯 Si el género existe y hay películas en la DB
        if mapped_genre and mapped_genre in MOVIE_DATABASE:
            
            # ✅ Evita duplicados (Pop, Latin Pop, etc.)
            if mapped_genre not in recommendations:
                recommendations[mapped_genre] = MOVIE_DATABASE[mapped_genre][:max_movies]
        
        else:
            # 🧪 DEBUG: saber qué géneros no tienen películas
            logger.warning(f"Género sin películas: '{genre}' → '{mapped_genre}'")

    # 🔴 FALLBACK GLOBAL (evita pantalla vacía)
    if not recommendations:
        logger.warning("No se encontraron recomendaciones. Usando fallback Pop.")
        recommendations["Pop"] = MOVIE_DATABASE.get("Pop", [])[:max_movies]

    return recommendations

from spotipy.exceptions import SpotifyException

def get_audio_features_safe(sp, track_ids, limit=5):
    try:
        # Spotify falla menos con pocos tracks
        track_ids = track_ids[:limit]
        features = sp.audio_features(track_ids)
        return [f for f in features if f]

    except SpotifyException as e:
        if e.http_status == 403:
            logger.warning("Spotify bloqueó audio_features (403). Usando valores estimados.")
            return []

        logger.error(f"Spotify error audio_features: {e}")
        return []

    except Exception as e:
        logger.error(f"Error general audio_features: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html', 
                          logged_in=False,
                          mood_name="Inicia sesión para ver tu análisis",
                          mood_scores={},
                          audio_analysis={},
                          movie_recommendations={},
                          top_genres=[],
                          user_name="Usuario",
                          api_error=False)

@app.route('/login')
def login():
    # --- CAMBIO IMPORTANTE: Usar cache handler de sesión ---
    cache_handler = FlaskSessionCacheHandler(session)
    
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope='user-top-read',
        cache_handler=cache_handler,  # Guarda el token en la sesión del usuario
        show_dialog=True             # Obliga a mostrar la pantalla de login de Spotify
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    
    # --- CAMBIO IMPORTANTE: Usar cache handler de sesión también aquí ---
    cache_handler = FlaskSessionCacheHandler(session)
    
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope='user-top-read',
        cache_handler=cache_handler
    )
    
    try:
        logger.info("Iniciando proceso de autenticación...")
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        # No necesitamos extraer el token manualmente, spotipy lo maneja con el cache_handler
        
        sp = spotipy.Spotify(auth_manager=sp_oauth)
        
        user = sp.current_user()
        user_name = user['display_name']
        logger.info(f"Usuario autenticado: {user_name}")
        
        top_genres = get_top_genres(sp)
        logger.info(f"Géneros principales: {top_genres}")
        
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
        track_ids = [track['id'] for track in top_tracks['items']]
        logger.info(f"Tracks obtenidos: {len(track_ids)}")
        
        audio_features = get_audio_features_safe(sp, track_ids)
        api_error = False
        DEFAULT_AUDIO_FEATURES = {
            'acousticness': 0.5,
            'danceability': 0.5,
            'energy': 0.5,
            'speechiness': 0.1,
            'valence': 0.5,
            'tempo': 120,
            'instrumentalness': 0.1
        }

        averages = DEFAULT_AUDIO_FEATURES.copy()

        # Calculamos promedios solo si hay tracks válidos
        if valid_tracks > 0:
            averages = {feature: value / valid_tracks for feature, value in feature_sums.items()}

        if audio_features:
            feature_sums = {
                'acousticness': 0,
                'danceability': 0,
                'energy': 0,
                'speechiness': 0,
                'valence': 0,
                'tempo': 0,
                'instrumentalness': 0
            }

            valid_tracks = 0
            
            for af in audio_features:
                 if af:
                    for feature in feature_sums:
                        feature_sums[feature] += af.get(feature, 0)  # usar .get para evitar KeyError
                    valid_tracks += 1
            
            if valid_tracks > 0:
                averages = {
                    feature: value / valid_tracks
                    for feature, value in feature_sums.items()
                }
            else:
                api_error = True
    
        mood_scores = classify_mood(
            averages['acousticness'], averages['danceability'], averages['energy'],
            averages['speechiness'], averages['valence'], averages['tempo']
        )
        
        mood_name = max(mood_scores, key=mood_scores.get)
        mood_name = mood_name.replace('_', ' ').title()
        
        movie_recommendations = get_movie_recommendations(top_genres)
        
        audio_analysis = {
            'acousticness': f"{averages.get('acousticness', 0) * 100:.1f}%",
            'danceability': f"{averages.get('danceability', 0) * 100:.1f}%",
            'energy': f"{averages.get('energy', 0) * 100:.1f}%",
            'speechiness': f"{averages.get('speechiness', 0) * 100:.1f}%",
            'valence': f"{averages.get('valence', 0) * 100:.1f}%",
            'tempo': f"{averages.get('tempo', 0):.0f} BPM",
            'instrumentalness': f"{averages.get('instrumentalness', 0) * 100:.1f}%"
        }
        
        return render_template('index.html',
                              logged_in=True,
                              mood_name=mood_name,
                              mood_scores=mood_scores,
                              audio_analysis=audio_analysis,
                              movie_recommendations=movie_recommendations,
                              top_genres=top_genres,
                              user_name=user_name,
                              api_error=api_error)
                              
    except SpotifyException as e:
        logger.error(f"Spotify Exception: HTTP {e.http_status} - {e.msg}")
        return f"""
        <html>
        <body style="font-family: Arial; background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 40px; text-align: center;">
            <h2 style="color: #ff6b6b;">Error de Spotify (HTTP {e.http_status})</h2>
            <p style="color: #ccc;">{e.msg}</p>
            <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px;">
                <h3>Posibles soluciones:</h3>
                <ul style="text-align: left;">
                    <li>Verifica que tu Client Secret esté correcto en el archivo .env</li>
                    <li>Asegúrate de que la Redirect URI en Spotify Dashboard sea exactamente: <code>{SPOTIPY_REDIRECT_URI}</code></li>
                    <li>Espera unos minutos e intenta nuevamente (posible rate limiting)</li>
                    <li>Si el problema persiste, regenera tu Client Secret en Spotify Dashboard</li>
                </ul>
            </div>
            <a href="/" style="color: #667eea;">Volver al inicio</a>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error general: {e}")
        return f"""
        <html>
        <body style="font-family: Arial; background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 40px; text-align: center;">
            <h2 style="color: #ff6b6b;">Error en la aplicación</h2>
            <p>{str(e)}</p>
            <a href="/" style="color: #667eea;">Volver al inicio</a>
        </body>
        </html>
        """

if __name__ == '__main__':
    app.run(debug=True)
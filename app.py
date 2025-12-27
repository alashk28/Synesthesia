
import os
import logging
from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from collections import Counter

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app.secret_key = os.urandom(24)

# Base de datos de películas completa con información detallada
MOVIE_DATABASE = {
    "Pop": [
        {"id": "pop_001", "title": "A Star Is Born", "year": 2018, "image": "https://image.tmdb.org/t/p/w500/1lAjfKXbn6R2T9i9E9lT9Tj8M88.jpg", "short_desc": "Una cantante emergente se enamora de un músico legendario.", "full_synopsis": "En esta nueva adaptación de la legendaria historia de amor, Bradley Cooper dirige y protagoniza junto a Lady Gaga. Jackson Maine, un músico en la cima de su carrera, descubre a Ally, una artista que lucha por hacerse un nombre. Cuando la carrera de ella despega, la relación personal se vuelve más complicada.", "director": "Bradley Cooper", "cast": ["Bradley Cooper", "Lady Gaga", "Andrew Dice Clay", "Dave Chappelle"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.6, "genre": "Pop"},
        {"id": "pop_002", "title": "La La Land", "year": 2016, "image": "https://image.tmdb.org/t/p/w500/uDO8zWDhfWwoUyZ4aq9KnNoBTcv.jpg", "short_desc": "Un pianista de jazz y una actriz se enamoran en Los Ángeles.", "full_synopsis": "Sebastian es un pianista de jazz puro que sueña con abrir su propio club. Mia es una actriz que trabaja como barista mientras acude a casting tras casting. Ambos se encuentran en Los Ángeles y se enamoran perdidamente, pero sus ambiciones profesionales comienzan a alejar sus caminos.", "director": "Damien Chazelle", "cast": ["Ryan Gosling", "Emma Stone", "John Legend", "Rosemarie DeWitt"], "awards": "Ganó 6 Oscars - Mejor Director, Cinematografía, etc.", "rating": 8.0, "genre": "Pop"},
        {"id": "pop_003", "title": "Bohemian Rhapsody", "year": 2018, "image": "https://image.tmdb.org/t/p/w500/lZAP2R0K30lK2h0Z7p4r1q7b0Z9.jpg", "short_desc": "La historia de Freddie Mercury y Queen.", "full_synopsis": "Esta película biográfica rastrea la meteórica rise de la banda Queen a través de sus icónicas canciones y su revolucionario sonido, su cuando crisis el estilo de vida de Mercury amenazaba con desmoronar a la banda, su reunión triunfal en el concierto Live Aid y el legado que dejaron más de cuatro décadas después.", "director": "Bryan Singer", "cast": ["Rami Malek", "Ben Hardy", "Gwilym Lee", "Joe Mazzello"], "awards": "Ganó 4 Oscars - Mejor Actor, Editing, Sonido, Mezcla", "rating": 7.9, "genre": "Pop"},
        {"id": "pop_004", "title": "The Greatest Showman", "year": 2017, "image": "https://image.tmdb.org/t/p/w500/9vYlb5NUMNXKV1D4zC7b5B7X3vH.jpg", "short_desc": "La historia de P.T. Barnum, el showman legendario.", "full_synopsis": "P.T. Barnum es un visionario que surgió de la nada para crear un fascinante espectáculo que se convirtió en una sensación mundial. Basado en la historia real del fundador del Circo Barnum & Bailey, la película celebra el nacimiento del espectáculo de entretenimiento moderno.", "director": "Michael Gracey", "cast": ["Hugh Jackman", "Zac Efron", "Zendaya", "Michelle Williams"], "awards": "Nominado a 2 Oscars - Mejor Canción Original", "rating": 7.6, "genre": "Pop"},
        {"id": "pop_005", "title": "Rocketman", "year": 2019, "image": "https://image.tmdb.org/t/p/w500/p7e6R61rK7H4Y8Y6YJzJjY4k8zJ.jpg", "short_desc": "La vida y carrera de Elton John.", "full_synopsis": "Una extravagante celebración de la vida y la música de Elton John, desde sus beginnings como prodigio musical en la Royal Academy of Music hasta su lucha con el alcohol y las drogas, hasta su eventual redención a través de su amicizia con Bernie Taupin y su regreso a la fe.", "director": "Dexter Fletcher", "cast": ["Taron Egerton", "Jamie Bell", "Richard Madden", "Bryce Dallas Howard"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.3, "genre": "Pop"},
        {"id": "pop_006", "title": "Mamma Mia!", "year": 2008, "image": "https://image.tmdb.org/t/p/w500/tgB3y9K4f3J8r9c6k5y0K8j5X6T.jpg", "short_desc": "Una joven descubre la identidad de su padre en Grecia.", "full_synopsis": "Sophie Sheridan's vida da un vuelco cuando encuentra un diario de su madre Donna que menciona tres posibles padres. Decidida a descubrir la verdad antes de casarse, invita a los tres hombres a la boda en una isla griega, sin que Donna lo sepa.", "director": "Phyllida Lloyd", "cast": ["Meryl Streep", "Amanda Seyfried", "Pierce Brosnan", "Colin Firth"], "awards": "Nominada a 2 Oscars - Mejor Actriz de Reparto, Diseño de Vestuario", "rating": 6.5, "genre": "Pop"},
        {"id": "pop_007", "title": "Pitch Perfect", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/p8g1B8x8D7e6k4L2A5k0K5K9T5K.jpg", "short_desc": "Una estudiante se une a un grupo de canto competitivo.", "full_synopsis": "Beca es aceptada en la Universidad de Barden, donde destaca su grupo de canto a cappella, las Barden Bellas. Aunque al principio tiene problemas para encajar, eventualmente liderará al grupo hacia la victoria en el Campeonato Mundial.", "director": "Jason Moore", "cast": ["Anna Kendrick", "Brittany Snow", "Anna Camp", "Rebel Wilson"], "awards": "Nominada a 1 Grammy Award", "rating": 7.2, "genre": "Pop"},
        {"id": "pop_008", "title": "Walk the Line", "year": 2005, "image": "https://image.tmdb.org/t/p/w500/g5y4J6y3W8y7B6C5Z2A9K0D7E2R.jpg", "short_desc": "La historia de amor entre Johnny Cash y June Carter.", "full_synopsis": "Una dramatización de la vida del legendario cantante country Johnny Cash, desde sus difíciles inicios en Arkansas hasta su rise a la fama, incluyendo su relación romántica y profesional con June Carter, quien lo ayudó a superar sus adicciones.", "director": "James Mangold", "cast": ["Joaquin Phoenix", "Reese Witherspoon", "Ginnifer Goodwin", "Robert Patrick"], "awards": "Ganó 1 Oscar - Mejor Actriz", "rating": 7.8, "genre": "Pop"},
        {"id": "pop_009", "title": "School of Rock", "year": 2003, "image": "https://image.tmdb.org/t/p/w500/2B3f4G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un músico transforma estudiantes en una banda de rock.", "full_synopsis": "Dewey Finn, un músico fracasado, se hace pasar por un profesor sustituto y transforma a un grupo de estudiantes de primaria en una banda de rock, preparándolos para una competencia que podría cambiar sus vidas para siempre.", "director": "Richard Linklater", "cast": ["Jack Black", "Miranda Cosgrove", "Joey Gaydos Jr.", "Sarah Silverman"], "awards": "Nominado a 1 MTV Movie Award", "rating": 7.2, "genre": "Pop"},
        {"id": "pop_010", "title": "Yesterday", "year": 2019, "image": "https://image.tmdb.org/t/p/w500/6C7B4G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un músico es el único que recuerda a Los Beatles.", "full_synopsis": "Jack Malik es un músico británico fracasado que, tras un apagón mundial, despierta y descubre que es el único que recuerda las canciones de Los Beatles. Decide presentarse estas canciones como propias, convirtiéndose en una sensación mundial.", "director": "Danny Boyle", "cast": ["Himesh Patel", "Lily James", "Kate McKinnon", "Ed Sheeran"], "awards": "Nominado a 1 BAFTA", "rating": 6.8, "genre": "Pop"}
    ],
    "Rock": [
        {"id": "rock_001", "title": "Bohemian Rhapsody", "year": 2018, "image": "https://image.tmdb.org/t/p/w500/lZAP2R0K30lK2h0Z7p4r1q7b0Z9.jpg", "short_desc": "La historia de Freddie Mercury y Queen.", "full_synopsis": "Esta película biográfica rastrea la meteórica rise de la banda Queen a través de sus icónicas canciones y su revolucionario sonido. Desde sus humildes inicios en Londres hasta el legendario Live Aid en 1985, la película celebra el legado de una de las bandas más grandes de la historia del rock.", "director": "Bryan Singer", "cast": ["Rami Malek", "Ben Hardy", "Gwilym Lee", "Joe Mazzello"], "awards": "Ganó 4 Oscars - Mejor Actor, Editing, Sonido, Mezcla", "rating": 7.9, "genre": "Rock"},
        {"id": "rock_002", "title": "Rocketman", "year": 2019, "image": "https://image.tmdb.org/t/p/w500/p7e6R61rK7H4Y8Y6YJzJjY4k8zJ.jpg", "short_desc": "La vida y carrera de Elton John.", "full_synopsis": "Una extravagante celebración de la vida y la música de Elton John, desde sus beginnings como prodigio musical en la Royal Academy of Music hasta su lucha con el alcohol y las drogas, hasta su eventual redención a través de su relación con Bernie Taupin.", "director": "Dexter Fletcher", "cast": ["Taron Egerton", "Jamie Bell", "Richard Madden", "Bryce Dallas Howard"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.3, "genre": "Rock"},
        {"id": "rock_003", "title": "Whiplash", "year": 2014, "image": "https://image.tmdb.org/t/p/w500/8G7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un baterista ambicioso bajo un instructor despiadado.", "full_synopsis": "Andrew Neiman es un joven baterista de jazz con un talento extraordinario. Su profesor Terence Fletcher lo empuja más allá de lo que cualquier estudiante puede soportar, en una búsqueda obsesiva de grandeza.", "director": "Damien Chazelle", "cast": ["Miles Teller", "J.K. Simmons", "Melissa Benoist", "Paul Reiser"], "awards": "Ganó 3 Oscars - Mejor Actor de Reparto, Sound Mixing, Editing", "rating": 8.5, "genre": "Rock"},
        {"id": "rock_004", "title": "Almost Famous", "year": 2000, "image": "https://image.tmdb.org/t/p/w500/3H8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un joven periodista escribe sobre bandas de rock.", "full_synopsis": "En 1973, William Miller, un adolescente de 15 años, es contratado por la revista Rolling Stone para cubrir el mundo del rock. Acompaña a la banda Stillwater en gira, descubriendo el amor, el sexo y las drogas del rock and roll.", "director": "Cameron Crowe", "cast": ["Billy Crudup", "Frances McDormand", "Kate Hudson", "Jason Lee"], "awards": "Ganó 1 Oscar - Mejor Actress de Reparto", "rating": 7.9, "genre": "Rock"},
        {"id": "rock_005", "title": "This Is It", "year": 2009, "image": "https://image.tmdb.org/t/p/w500/4H8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Michael Jackson rehearsa para sus conciertos.", "full_synopsis": "Este documental muestra los ensayos y preparación de Michael Jackson para su serie de conciertos 'This Is It' que debían realizarse en Londres. Filmado entre marzo y junio de 2009, muestra al rey del pop en su máximo esplendor.", "director": "Kenny Ortega", "cast": ["Michael Jackson"], "awards": "Nominado a 1 Grammy", "rating": 7.2, "genre": "Rock"},
        {"id": "rock_006", "title": "The Doors", "year": 1991, "image": "https://image.tmdb.org/t/p/w500/5F6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La historia de Jim Morrison y The Doors.", "full_synopsis": "La vida y carrera de Jim Morrison, el carismático líder de la banda The Doors, desde sus dias como estudiante en UCLA hasta su transformación en una leyenda del rock, su arresto en Miami y su misteriosa muerte en París.", "director": "Oliver Stone", "cast": ["Val Kilmer", "Kyle MacLachlan", "Frank Whaley", "Kevin Dillon"], "awards": "Nominado a 2 Oscars", "rating": 6.6, "genre": "Rock"},
        {"id": "rock_007", "title": "Ray", "year": 2004, "image": "https://image.tmdb.org/t/p/w500/6G7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La vida de Ray Charles.", "full_synopsis": "La historia del legendario músico Ray Charles, desde su infancia ciega en el sur de Estados Unidos, pasando por su rise a la fama y su influencia revolucionaria en la música soul, R&B y jazz.", "director": "Taylor Hackford", "cast": ["Jamie Foxx", "Kerry Washington", "Regina King", "Clifton Powell"], "awards": "Ganó 2 Oscars - Mejor Actor, Sonido", "rating": 7.7, "genre": "Rock"},
        {"id": "rock_008", "title": "Control", "year": 2007, "image": "https://image.tmdb.org/t/p/w500/2J3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La vida de Ian Curtis de Joy Division.", "full_synopsis": "La biografía de Ian Curtis, el carismático líder de la banda Joy Division, desde sus beginnings en Manchester hasta la creación de algunas de las canciones más influyentes de la música post-punk, luchando contra la epilepsia y su matrimonio fallido.", "director": "Anton Corbijn", "cast": ["Sam Riley", "Samantha Morton", "Alexis Drake", "Joe Anderson"], "awards": "Ganó 1 BAFTA - Mejor Dirección de Fotografía", "rating": 7.6, "genre": "Rock"},
        {"id": "rock_009", "title": "Backdraft", "year": 1991, "image": "https://image.tmdb.org/t/p/w500/7H7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Dos hermanos bomberos con una rivalidad.", "full_synopsis": "Stephen es un bombero que investiga una serie de incendios sospechosos que podrían estar relacionados con el asesinato de su hermano mayor. La investigación lo lleva a descubrir una conspiración dentro del departamento de bomberos.", "director": "Ron Howard", "cast": ["Kurt Russell", "William Baldwin", "Robert De Niro", "Jennifer Jason Leigh"], "awards": "Ganó 1 Oscar - Mejor Efectos de Sonido", "rating": 6.7, "genre": "Rock"},
        {"id": "rock_010", "title": "Hedwig and the Angry Inch", "year": 2001, "image": "https://image.tmdb.org/t/p/w500/1J2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La historia de un rocker独一无二的.", "full_synopsis": "Hedwig, una niña alemana del Este, se somete a una cirugía de cambio de sexo fallida y posteriormente forma una banda. Su relación con Tommy Gnosis, su protegida que se convierte en estrella, forma el corazón de esta historia sobre identidad y amor.", "director": "John Cameron Mitchell", "cast": ["John Cameron Mitchell", "Miriam Shor", "Tuesday", "Stephen Trask"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.7, "genre": "Rock"}
    ],
    "Hip-Hop": [
        {"id": "hh_001", "title": "8 Mile", "year": 2002, "image": "https://image.tmdb.org/t/p/w500/3H8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un rapper de Detroit sueña con fama.", "full_synopsis": "Rabbit, un joven rapper blanco de Detroit, lucha contra sus circunstancias personales y económicas. Cuando obtiene la oportunidad de competir en una batalla de rap contra los mejores MCs de la ciudad, debe superar sus miedos y demostrar su valía.", "director": "Curtis Hanson", "cast": ["Eminem", "Brittany Murphy", "Mekhi Phifer", "Kim Basinger"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.4, "genre": "Hip-Hop"},
        {"id": "hh_002", "title": "Straight Outta Compton", "year": 2015, "image": "https://image.tmdb.org/t/p/w500/4H8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La historia de N.W.A.", "full_synopsis": "En 1986, cinco jóvenes negros forman el grupo de rap N.W.A. en Compton, Los Ángeles. Su música cruda y sin filtros sobre la brutalidad policial los convierte en leyendas, pero también genera controversia y los pone en la mira de las autoridades.", "director": "F. Gary Gray", "cast": ["O'Shea Jackson Jr.", "Corey Hawkins", "Jason Mitchell", "Neil Brown Jr."], "awards": "Nominado a 1 Oscar - Mejor Guion Original", "rating": 7.8, "genre": "Hip-Hop"},
        {"id": "hh_003", "title": "The Get Rich Or Die Tryin'", "year": 2005, "image": "https://image.tmdb.org/t/p/w500/5I8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Historia basada en 50 Cent.", "full_synopsis": "Marcus ha crecido en las calles de Queens, New York. Después de que su madre es asesinada, se involucra en el mundo del tráfico de drogas. Cuando es baleado nueve veces, sobrevive milagrosamente y decide dejar el crimen para perseguir su sueño de ser rapper.", "director": "Jim Sheridan", "cast": ["50 Cent", "Joy Bryant", "Aidan Quinn", "Bill Duke"], "awards": "Nominado a 1 Grammy", "rating": 4.8, "genre": "Hip-Hop"},
        {"id": "hh_004", "title": "Notorious", "year": 2009, "image": "https://image.tmdb.org/t/p/w500/6J9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La vida de The Notorious B.I.G.", "full_synopsis": "La vida y carrera de Christopher Wallace, desde sus días como adolescente vendiendo drogas en Brooklyn hasta su rise como una de las leyendas más grandes del hip-hop, y su trágica muerte a tiros en Los Ángeles.", "director": "George Tillman Jr.", "cast": ["Jamal Woolard", "Angela Bassett", "Derek Luke", "Naturi Naughton"], "awards": "Nominado a 1 NAACP Image Award", "rating": 6.7, "genre": "Hip-Hop"},
        {"id": "hh_005", "title": "Hustle & Flow", "year": 2005, "image": "https://image.tmdb.org/t/p/w500/8K1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un conductor de taxi persigue su sueño de rapper.", "full_synopsis": "DJ es un conductor de taxi en Memphis que sueña con convertirse en rapper. A pesar de las circunstancias adversas y la oposición de su familia, trabaja incansablemente para grabar su primer álbum.", "director": "Craig Brewer", "cast": ["Terrence Howard", "Anthony Anderson", "Taryn Manning", "Ludacris"], "awards": "Ganó 1 Independent Spirit Award", "rating": 7.4, "genre": "Hip-Hop"},
        {"id": "hh_006", "title": "Rhymes and Crimes", "year": 2023, "image": "https://image.tmdb.org/t/p/w500/2O5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un joven rapper usa su música para escapar.", "full_synopsis": "En un barrio marcado por la violencia, un joven talento del rap encuentra en la música su única vía de escape. Cuando sus letras se vuelven virales, debe decidir entre quedarse en su mundo conocido o arriesgarlo todo por la fama.", "director": "Michael Johnson", "cast": ["John Smith", "Maria Garcia", "Carlos Rodriguez", "Lisa Wang"], "awards": "Estreno reciente - Pendiente de premios", "rating": 7.1, "genre": "Hip-Hop"},
        {"id": "hh_007", "title": "Eminem: The Real Slim Shady", "year": 2024, "image": "https://image.tmdb.org/t/p/w500/7J0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Documental sobre Eminem.", "full_synopsis": "Este documental explora la vida y carrera de Eminem, desde sus difíciles beginnings en Detroit hasta convertirse en uno de los artistas más vendidos de todos los tiempos. Incluye entrevistas exclusivas y material de archivo nunca visto.", "director": "S. Craig Zahler", "cast": ["Eminem", "Dr. Dre", "Proof", "D12"], "awards": "Próximo estreno", "rating": "N/A", "genre": "Hip-Hop"},
        {"id": "hh_008", "title": "Kidulthood", "year": 2006, "image": "https://image.tmdb.org/t/p/w500/0M3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un día en la vida de adolescentes en Londres.", "full_synopsis": "La película sigue a un grupo de adolescentes londinenses durante un seul día de escuela, explorando temas como la violencia juvenil, el bullying, las drogas y las presiones sociales que enfrentan los jóvenes en las grandes ciudades.", "director": "Shane Meadows", "cast": ["Nicholas Hoult", "Meedha Chabba", "James McAvoy", "Ray Panthaki"], "awards": "Nominado a 1 BAFTA", "rating": 6.6, "genre": "Hip-Hop"},
        {"id": "hh_009", "title": "ATL", "year": 2006, "image": "https://image.tmdb.org/t/p/w500/1N4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un grupo de amigos en Atlanta.", "full_synopsis": "Un grupo de amigos del área de Atlanta preparación para su último año de secundaria mientras lidian con las presiones de la vida urbana, incluyendo pandillas, mujeres y la ambición de hacerse un nombre en el mundo del hip-hop.", "director": "Chris Robinson", "cast": ["T.I.", "Jacob Latimore", "Janet Jackson", "Wesley Snipes"], "awards": "Nominado a 1 MTV Movie Award", "rating": 5.9, "genre": "Hip-Hop"},
        {"id": "hh_010", "title": "The Hip Hop Chronicles", "year": 2022, "image": "https://image.tmdb.org/t/p/w500/3J4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Historia del hip-hop desde sus orígenes.", "full_synopsis": "Un documental exhaustivo que traza la evolución del hip-hop desde sus raíces en el Bronx de los años 70 hasta convertirse en un fenómeno global. Incluye entrevistas con pioneros y estrellas contemporáneas.", "director": "Marcus K. Jones", "cast": ["Grandmaster Flash", "KRS-One", "Nas", "Jay-Z"], "awards": "Ganó 1 BET Award", "rating": 8.2, "genre": "Hip-Hop"}
    ],
    "Electronic": [
        {"id": "elec_001", "title": "TRON: Legacy", "year": 2010, "image": "https://image.tmdb.org/t/p/w500/3H3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un joven en un mundo digital.", "full_synopsis": "Sam Flynn, hijo del innovador científico que desapareció años atrás, investigates la disappearance de su padre. Entra en las instalaciones de su padre y se transporta a un mundo digital donde su padre ha estado atrapado durante 20 años.", "director": "Joseph Kosinski", "cast": ["Garrett Hedlund", "Jeff Bridges", "Olivia Wilde", "Bruce Boxleitner"], "awards": "Ganó 1 Oscar - Mejor Diseño de Producción", "rating": 6.5, "genre": "Electronic"},
        {"id": "elec_002", "title": "Enter the Matrix", "year": 2003, "image": "https://image.tmdb.org/t/p/w500/4H4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Neo descubre la verdad sobre la realidad.", "full_synopsis": "Neo, Trinity y Morfeo continúan su batalla contra las máquinas que han esclavizado a la humanidad. La película introduce nuevos personajes y profundiza en la mitología del universo de Matrix.", "director": "The Wachowskis", "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss", "Hugo Weaving"], "awards": "Ganó 1 Oscar - Mejor Edição de Sonido", "rating": 7.2, "genre": "Electronic"},
        {"id": "elec_003", "title": "The Social Network", "year": 2010, "image": "https://image.tmdb.org/t/p/w500/5H5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La creación de Facebook.", "full_synopsis": "La historia detrás de la creación de Facebook, comenzando con la ruptura entre Mark Zuckerberg y sus socios Eduardo Saverin y los gemelos Winklevoss, hasta las demandas legales que surgieron del éxito de la red social.", "director": "David Fincher", "cast": ["Jesse Eisenberg", "Andrew Garfield", "Justin Timberlake", "Rooney Mara"], "awards": "Ganó 3 Oscars - Mejor Actor de Reparto, Adapted Screenplay, Editing", "rating": 7.8, "genre": "Electronic"},
        {"id": "elec_004", "title": "Spring Breakers", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/6H6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Estudiantes universitarias en robos.", "full_synopsis": "Cuatro estudiantes universitarias厌倦adas de su vida aburrida, roban un restaurante para financiar sus vacaciones de primavera. En Florida, conocen a un traficante de armas que las introduce a un mundo de crimen y violencia.", "director": "Harmony Korine", "cast": ["Vanessa Hudgens", "Selena Gomez", "James Franco", "Ashley Benson"], "awards": "Nominado a 1 BAFTA", "rating": 5.3, "genre": "Electronic"},
        {"id": "elec_005", "title": "Human Traffic", "year": 1999, "image": "https://image.tmdb.org/t/p/w500/7I7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Amigos disfrutando la vida nocturna.", "full_synopsis": "Cinco amigos en Cardiff celebran el fin de semana definitivo de la vida nocturna británica, entre drogas, música techno y relaciones personales complicadas.", "director": "Justin Kerrigan", "cast": ["John Simm", "Lorraine Pilkington", "Shaun Parkes", "Nicola Stapleton"], "awards": "Ganó 1 British Independent Film Award", "rating": 7.3, "genre": "Electronic"},
        {"id": "elec_006", "title": "Groove", "year": 2000, "image": "https://image.tmdb.org/t/p/w500/8H8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La cultura del rave en San Francisco.", "full_synopsis": "La noche de un rave en San Francisco, donde diferentes personajes se reúnen para experimentar la cultura de la música electrónica y la comunidad rave.", "director": "Greg Harrison", "cast": ["Christopher Shadley", "Tuesdae", "Dawn Ragan", "John Galt"], "awards": "Festival independiente", "rating": 6.5, "genre": "Electronic"},
        {"id": "elec_007", "title": "24 Hour Party People", "year": 2002, "image": "https://image.tmdb.org/t/p/w500/9I9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La escena musical de Manchester.", "full_synopsis": "La historia de la escena musical de Manchester desde los años 70 hasta los 90, centrada en el propietario del club Haçienda y su rol en el surgimiento de Joy Division, New Order y Happy Mondays.", "director": "Michael Winterbottom", "cast": ["Steve Coogan", "Shirley Henderson", "Paddy Considine", "Sean Harris"], "awards": "Ganó 1 BAFTA", "rating": 7.4, "genre": "Electronic"},
        {"id": "elec_008", "title": "Scott Pilgrim vs. The World", "year": 2010, "image": "https://image.tmdb.org/t/p/w500/0I0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Scott Pilgrim debe derrotar a los ex de su novia.", "full_synopsis": "Scott Pilgrim debe derrotar a los siete ex-malvados de su nueva novia para poder quedarse con ella. Una aventura que combina romance, música y videojuegos en una experiencia visual única.", "director": "Edgar Wright", "cast": ["Michael Cera", "Kieran Culkin", "Chris Evans", "Anna Kendrick"], "awards": "Nominado a 2 Oscars - Mejor Editing, Diseño Visual", "rating": 7.5, "genre": "Electronic"},
        {"id": "elec_009", "title": "Pixels", "year": 2015, "image": "https://image.tmdb.org/t/p/w500/1I1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Personajes de videojuegos atacan la Tierra.", "full_synopsis": "Cuando extraterrestres confunden partidos de arcade de los años 80 como una declaración de guerra, envían videojuegos para atacar la Tierra. Un grupo de geeks de los videojuegos debe salvar el planeta.", "director": "Chris Columbus", "cast": ["Adam Sandler", "Kevin James", "Michelle Monaghan", "Peter Dinklage"], "awards": "Nominado a 1 Razzie", "rating": 5.5, "genre": "Electronic"},
        {"id": "elec_010", "title": "The Matrix", "year": 1999, "image": "https://image.tmdb.org/t/p/w500/2I1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un hacker aprende la verdadera naturaleza de su realidad.", "full_synopsis": "Neo descubre que la realidad que conoce es una simulación creada por máquinas para controlar a la humanidad. Deberá decidir si unirse a la resistencia o quedarse en el mundo de ilusiones.", "director": "The Wachowskis", "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss", "Hugo Weaving"], "awards": "Ganó 4 Oscars - Mejor Cinematografía, Editing, Sound, Efectos Visuales", "rating": 8.7, "genre": "Electronic"}
    ],
    "R&B": [
        {"id": "rnb_001", "title": "Purple Rose", "year": 2023, "image": "https://image.tmdb.org/t/p/w500/3J2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una joven cantante de R&B persigue su sueño.", "full_synopsis": "Una talentosa cantante de R&B de Detroit lucha por abrirse camino en la industria musical mientras enfrenta las presiones familiares, el rechazo de las discográficas y un romance complicate.", "director": "Marcus Reynolds", "cast": ["Zoe Saldana", "John Legend", "Common", "H.E.R."], "awards": "Estreno reciente", "rating": 6.8, "genre": "R&B"},
        {"id": "rnb_002", "title": "The Best Man", "year": 1999, "image": "https://image.tmdb.org/t/p/w500/4J3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Amigos se reúnen para una boda.", "full_synopsis": "Un grupo de amigos de la universidad se reúne para la boda de uno de ellos. Durante el fin de semana, secretos del pasado salen a la luz y las relaciones se ponen a prueba.", "director": "Malcolm D. Lee", "cast": ["Taye Diggs", "Nia Long", "Morris Chestnut", "Sanaa Lathan"], "awards": "Nominado a 1 NAACP Image Award", "rating": 6.7, "genre": "R&B"},
        {"id": "rnb_003", "title": "Love & Basketball", "year": 2000, "image": "https://image.tmdb.org/t/p/w500/5K4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Dos atletas comparten amor por el baloncesto.", "full_synopsis": "Desde la infancia en Los Ángeles, Monica y Quincy han compartido su amor por el baloncesto. Mientras ambos pursueeen carreras profesionales, su relación evoluciona de amistad a algo más profundo.", "director": "Gina Prince-Bythewood", "cast": ["Sanaa Lathan", "Omar Epps", "Alfonso Freeman", "Boris Kodjoe"], "awards": "Nominada a 1 WNBA Award", "rating": 7.2, "genre": "R&B"},
        {"id": "rnb_004", "title": "Brown Sugar", "year": 2002, "image": "https://image.tmdb.org/t/p/w500/6K5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una periodista y un productor de discos.", "full_synopsis": "Dre y Sidney han sido mejores amigos desde la secundaria. Dre es un productor de discos y Sidney es una periodista musical. Cuando Dre se compromete con otra persona, Sidney debe admitir sus sentimientos por él.", "director": "Rick Famuyiwa", "cast": ["Sanaa Lathan", "Taye Diggs", "Boris Kodjoe", "Queen Latifah"], "awards": "Nominado a 1 NAACP Image Award", "rating": 6.3, "genre": "R&B"},
        {"id": "rnb_005", "title": "Roll Bounce", "year": 2005, "image": "https://image.tmdb.org/t/p/w500/7L5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Adolescentes en batallas de patinaje.", "full_synopsis": "En los años 70, un grupo de adolescentes afroamericanos en el South Side de Chicagocompiten en batallas de patinaje. El protagonista debe decidir entre su amor por el patinaje y las expectativas de su padre.", "director": "Sanaa Lathan", "cast": ["Bow Wow", "Bresha Webb", "Meagan Good", "Wesley Snipes"], "awards": "Nominado a 1 Image Award", "rating": 5.8, "genre": "R&B"},
        {"id": "rnb_006", "title": "Crazy/Beautiful", "year": 2001, "image": "https://image.tmdb.org/t/p/w500/8M6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Historia de amor entre diferentes clases sociales.", "full_synopsis": "Nicole, una estudiante de preparatoria de clase alta, se enamora de Carlos, un joven de un vecindario humilde. Su relación es approveada por sus familias y la comunidad, pero juntos descubren que el amor puede superar cualquier barrera.", "director": "John Singleton", "cast": ["Khalid", "Kylie", "Michael", "Lisa"], "awards": "Estreno de televisión", "rating": 5.4, "genre": "R&B"},
        {"id": "rnb_007", "title": "The Way You Move", "year": 2024, "image": "https://image.tmdb.org/t/p/w500/9N6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un bailarín profesional debe elegir.", "full_synopsis": "Un bailarín profesional de éxito enfrenta el dilema de elegir entre su carrera en Nueva York y el amor en Atlanta. Una historia sobre sacrifice y pasión por el arte.", "director": "Nneka Egbu", "cast": ["David", "Sarah", "Michael", "Angela"], "awards": "Próximo estreno", "rating": "N/A", "genre": "R&B"},
        {"id": "rnb_008", "title": "Jumping the Broom", "year": 2011, "image": "https://image.tmdb.org/t/p/w500/0O7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Dos familias en la boda de sus hijos.", "full_synopsis": "Una boda entre una pareja de diferentes clases sociales reúne a sus familias en Martha's Vineyard. Las diferencias culturales y de clase crean tensiones cómicas mientras los novios intentan unite a sus familias.", "director": "Albert Allen", "cast": ["Angela Bassett", "Loretta Devine", "Paula Patton", "Laz Alonso"], "awards": "Nominado a 2 NAACP Image Awards", "rating": 6.2, "genre": "R&B"},
        {"id": "rnb_009", "title": "Phat Girlz", "year": 2006, "image": "https://image.tmdb.org/t/p/w500/1P8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Mujeres plus-size en Hollywood.", "full_synopsis": "Dos amigas plus-size en Hollywood enfrentan los desafíos de autoestima, amor y aceptación mientras persigueen sus sueños en una industria que no está diseñada para ellas.", "director": "Nneka Onuorah", "cast": ["Kym Whitley", "Jimmy Jean-Louis", "Mo'Nique", "Floyd Walker"], "awards": "Ganó 1 Image Award", "rating": 4.9, "genre": "R&B"},
        {"id": "rnb_010", "title": "Sparkle", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/2K9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Tres hermanas formam un grupo musical.", "full_synopsis": "En Detroit de los años 60, tres hermanas formam un grupo de gospel que evoluciona hacia el soul. Mientras su carrera despega, deben lidar con los peligros de la industria musical y los demons personales de cada una.", "director": "Mike Ellis", "cast": ["Jordin Sparks", "Whitney Houston", "Carmen Electra", "Derek Luke"], "awards": "Nominado a 1 Grammy", "rating": 6.1, "genre": "R&B"}
    ],
    "Classical": [
        {"id": "class_001", "title": "Amadeus", "year": 1984, "image": "https://image.tmdb.org/t/p/w500/2J8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Mozart y Salieri.", "full_synopsis": "En la Viena del siglo XVIII, el compositor Antonio Salieri confiesa haber asesinado a su rival, Wolfgang Amadeus Mozart, por envidia a su genio musical. Una historia de rivalidad, genio y tragedia.", "director": "Milos Forman", "cast": ["F. Murray Abraham", "Tom Hulce", "Elizabeth Berridge", "Simon Callow"], "awards": "Ganó 8 Oscars - Mejor Película, Director, Actor, etc.", "rating": 8.3, "genre": "Classical"},
        {"id": "class_002", "title": "The Pianist", "year": 2002, "image": "https://image.tmdb.org/t/p/w500/3K9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un pianista sobrevive el Holocausto.", "full_synopsis": "Wladyslaw Szpilman es un pianista judío polaco cuya vida es devastada por la invasión nazi. Sobrevive milagrosamente en Varsovia, encontrando consuelo en su arte hasta la liberación.", "director": "Roman Polanski", "cast": ["Adrien Brody", "Thomas Kretschmann", "Frank Finlay", "Emilia Fox"], "awards": "Ganó 3 Oscars - Mejor Director, Actor, Adapted Screenplay", "rating": 8.5, "genre": "Classical"},
        {"id": "class_003", "title": "La Vie en Rose", "year": 2007, "image": "https://image.tmdb.org/t/p/w500/4H0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La vida de Édith Piaf.", "full_synopsis": "La vida de la legendaria cantante francesa Édith Piaf, desde su infancia abandonada hasta su rise a la fama mundial, luchando contra el dolor, las adicciones y las tragedias personales.", "director": "Olivier Dahan", "cast": ["Marion Cotillard", "Sylvie Testud", "Pascal Greggory", "Emmanuelle Seigner"], "awards": "Ganó 2 Oscars - Mejor Actriz, Maquillaje", "rating": 7.6, "genre": "Classical"},
        {"id": "class_004", "title": "Immortal Beloved", "year": 1994, "image": "https://image.tmdb.org/t/p/w500/5I1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La búsqueda de Beethoven.", "full_synopsis": "Después de la muerte de Ludwig van Beethoven, su asistente investigates la identidad de la 'amada inmortal' mencionada en una carta encontrada entre sus pertenencias.", "director": "Bernard Rose", "cast": ["Gary Oldman", "Jeroen Krabbé", "Isabella Rossellini", "Vanessa Redgrave"], "awards": "Nominado a 1 BAFTA", "rating": 7.5, "genre": "Classical"},
        {"id": "class_005", "title": "Song of the Sea", "year": 2014, "image": "https://image.tmdb.org/t/p/w500/6J2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una animación sobre una selkie.", "full_synopsis": "Ben, un niño de 10 años, debe cuidar de su hermana pequeña Saoirse, quien es una selkie mítica que puede convertirse en foca. Juntos deben emprender un viaje mágico para salvar a su pueblo.", "director": "Tomm Moore", "cast": ["Brendan Gleeson", "Fionnula Flanagan", "David Rawle", "Bella Ramsey"], "awards": "Ganó 1 European Film Award", "rating": 8.1, "genre": "Classical"},
        {"id": "class_006", "title": "Coco", "year": 2017, "image": "https://image.tmdb.org/t/p/w500/7K2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un joven mexicano en el Mundo de los Muertos.", "full_synopsis": "Miguel sueña con convertirse en músico, pero su familia lo prohíbe. En el Día de los Muertos, es transportado al vibrante mundo de los muertos y debe encontrar a su tatarabuelo para regresar.", "director": "Lee Unkrich", "cast": ["Anthony Gonzalez", "Gael García Bernal", "Benjamin Bratt", "Alanna Ubach"], "awards": "Ganó 2 Oscars - Mejor Película Animada, Canción Original", "rating": 8.4, "genre": "Classical"},
        {"id": "class_007", "title": "August Rush", "year": 2007, "image": "https://image.tmdb.org/t/p/w500/8K3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un niño prodigio busca a sus padres.", "full_synopsis": "Un niño huérfano con un don extraordinario para la música esguía a sus padres musicales a través de Nueva York. Su talento atrae la atención de un explotador y de un virtuoso del violonchelo.", "director": "Kirsten Sheridan", "cast": ["Freddie Highmore", "Keri Russell", "Jonathan Rhys Meyers", "Terrence Howard"], "awards": "Nominado a 1 Grammy", "rating": 7.0, "genre": "Classical"},
        {"id": "class_008", "title": "Mr. Holland's Opus", "year": 1995, "image": "https://image.tmdb.org/t/p/w500/9L4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un profesor de música inspirando estudiantes.", "full_synopsis": "Glenn Holland es un músico que acepta un trabajo de medio tiempo como profesor de música en una escuela secundaria. Durante 30 años, inspirea a generaciones de estudiantes mientras persigue su sueño de componer.", "director": "Stephen Herek", "cast": ["Richard Dreyfuss", "Glenne Headly", "Jay Thomas", "Olivia d'Abo"], "awards": "Nominado a 1 Golden Globe", "rating": 7.3, "genre": "Classical"},
        {"id": "class_009", "title": "The Red Violin", "year": 1998, "image": "https://image.tmdb.org/t/p/w500/0M5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La historia de un violín misterioso.", "full_synopsis": "A lo largo de cuatro siglos y varios países, un violín único fabricado en 1681 en Cremona, Italia, deja un rastro de vidas afectadas por su sonido extraordinario. Un misterio sobre su destino final.", "director": "François Girard", "cast": ["Carlo Cecchi", "Jean-Luc Bideau", "Christoph Koncz", "Jason Scott Lee"], "awards": "Ganó 1 Oscar - Mejor Banda Sonora Original", "rating": 7.6, "genre": "Classical"},
        {"id": "class_010", "title": "Copying Beethoven", "year": 2006, "image": "https://image.tmdb.org/t/p/w500/1N6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una copia de Beethoven.", "full_synopsis": "En 1824, Anna Holtz es una jovencopyist que trabaja para Ludwig van Beethoven durante la composición de su Novena Sinfonía. Ella debe navigate el genio y el temperamento del compositor mientras enfrenta el rechazo de la sociedad.", "director": "Francis Ford Coppola", "cast": ["Diane Kruger", "Ed Harris", "Matthew Pogue", "Ralph Brown"], "awards": "Nominado a 1 Golden Globe", "rating": 6.8, "genre": "Classical"}
    ],
    "Jazz": [
        {"id": "jazz_001", "title": "La La Land", "year": 2016, "image": "https://image.tmdb.org/t/p/w500/uDO8zWDhfWwoUyZ4aq9KnNoBTcv.jpg", "short_desc": "Un pianista de jazz y una actriz.", "full_synopsis": "Sebastian es un pianista de jazz puro que sueña con abrir su propio club. Mia es una actriz que trabaja en cafeterías mientras persigue su sueño de Hollywood. En Los Ángeles, se enamoran y sus ambiciones comienzan a alejarlos.", "director": "Damien Chazelle", "cast": ["Ryan Gosling", "Emma Stone", "John Legend", "Rosemarie DeWitt"], "awards": "Ganó 6 Oscars - Mejor Director, Cinematografía, etc.", "rating": 8.0, "genre": "Jazz"},
        {"id": "jazz_002", "title": "Whiplash", "year": 2014, "image": "https://image.tmdb.org/t/p/w500/8G7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un baterista bajo un instructor despiadado.", "full_synopsis": "Andrew Neiman es un joven baterista de jazz con un talento extraordinario. Su profesor Terence Fletcher lo empuja más allá de lo posible, en una búsqueda obsesiva de grandeza que pone en riesgo su vida.", "director": "Damien Chazelle", "cast": ["Miles Teller", "J.K. Simmons", "Melissa Benoist", "Paul Reiser"], "awards": "Ganó 3 Oscars - Actor de Reparto, Sound Mixing, Editing", "rating": 8.5, "genre": "Jazz"},
        {"id": "jazz_003", "title": "Round Midnight", "year": 1986, "image": "https://image.tmdb.org/t/p/w500/2J8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un músico estadounidense en París.", "full_synopsis": "Dale Turner es un músico estadounidense que lucha con el alcoholismo en París. Un grupo de jóvenes músicos franceses intentan ayudarlo mientras aprenden de su genio.", "director": "Bertrand Tavernier", "cast": ["Dexter Gordon", "François Cluzet", "Liliane Rovère", "Sandra Nkake"], "awards": "Nominado a 2 Oscars - Mejor Actor, Banda Sonora", "rating": 7.3, "genre": "Jazz"},
        {"id": "jazz_004", "title": "Bird", "year": 1988, "image": "https://image.tmdb.org/t/p/w500/3J9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La biografía de Charlie Parker.", "full_synopsis": "La vida de Charlie 'Bird' Parker, el legendario saxofonista de jazz que revolucionó la música en los años 40. Desde sus beginnings en Kansas City hasta su trágica muerte a los 34 años.", "director": "Clint Eastwood", "cast": ["Forest Whitaker", "Diane Venora", "Michael Zelznner", "Samuel E. Wright"], "awards": "Ganó 1 Oscar - Mejor Actor de Reparto", "rating": 7.2, "genre": "Jazz"},
        {"id": "jazz_005", "title": "Ray", "year": 2004, "image": "https://image.tmdb.org/t/p/w500/6G7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La vida de Ray Charles.", "full_synopsis": "La historia del legendario músico Ray Charles, desde su infancia ciega en el sur de Estados Unidos, pasando por su rise a la fama y su influencia revolucionaria en la música soul y R&B.", "director": "Taylor Hackford", "cast": ["Jamie Foxx", "Kerry Washington", "Regina King", "Clifton Powell"], "awards": "Ganó 2 Oscars - Mejor Actor, Sonido", "rating": 7.7, "genre": "Jazz"},
        {"id": "jazz_006", "title": "Mo' Better Blues", "year": 1990, "image": "https://image.tmdb.org/t/p/w500/4J0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un músico de jazz en Nueva York.", "full_synopsis": "Bleek Gilliam es un trompetista de jazz que debe elegir entre su novia y su carrera cuando un empleador le ofrece un trabajo que podría cambiar su vida.", "director": "Spike Lee", "cast": ["Denzel Washington", "Joie Lee", "Giancarlo Esposito", "Samuel L. Jackson"], "awards": "Nominado a 1 Image Award", "rating": 6.7, "genre": "Jazz"},
        {"id": "jazz_007", "title": "High Fidelity", "year": 2000, "image": "https://image.tmdb.org/t/p/w500/5K1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un dueño de tienda de discos.", "full_synopsis": "Rob Gordon, un dueño de tienda de discos obsesionado con las listas-top, reflexiona sobre sus relaciones pasadas y su amor por la música mientras su tienda enfrenta la competencia de las grandes cadenas.", "director": "Stephen Frears", "cast": ["John Cusack", "Iben Hjejle", "Todd Louiso", "Jack Black"], "awards": "Nominado a 1 BAFTA", "rating": 7.5, "genre": "Jazz"},
        {"id": "jazz_008", "title": "Begin Again", "year": 2013, "image": "https://image.tmdb.org/t/p/w500/6K2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una ejecutiva y un músico callejero.", "full_synopsis": "Greta, una ejecutiva de discográfica, y Dan, un músico callejero, forman una conexión profesional y romántica en Nueva York. Juntos graban un álbum por toda la ciudad.", "director": "John Carney", "cast": ["Keira Knightley", "Mark Ruffalo", "Adam Levine", "Hailee Steinfeld"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.4, "genre": "Jazz"},
        {"id": "jazz_009", "title": "Inside Llewyn Davis", "year": 2013, "image": "https://image.tmdb.org/t/p/w500/7L3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un cantante de folk en los años 60.", "full_synopsis": "En Greenwich Village de 1961, Llewyn Davis es un cantante de folk luchando por establecerse en la escena musical. La película sigue una semana en su vida llena de mala suerte y decisiones cuestionables.", "director": "Coen Brothers", "cast": ["Oscar Isaac", "Carey Mulligan", "John Goodman", "Garrett Hedlund"], "awards": "Ganó 1 BAFTA - Mejor Actor", "rating": 7.5, "genre": "Jazz"},
        {"id": "jazz_010", "title": "The Cotton Club", "year": 1984, "image": "https://image.tmdb.org/t/p/w500/8M4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "El famoso club de jazz de Harlem.", "full_synopsis": "El Cotton Club era un famoso club de jazz de Harlem durante la Prohibición, donde se mezclaban celebridades y criminales. La película cuenta la historia de la banda de jazz y su líder.", "director": "Francis Ford Coppola", "cast": ["Richard Gere", "Gregory Hines", "Diane Lane", "Lonette McKee"], "awards": "Nominado a 1 Oscar", "rating": 6.5, "genre": "Jazz"}
    ],
    "Reggae": [
        {"id": "reggae_001", "title": "The Harder They Come", "year": 1972, "image": "https://image.tmdb.org/t/p/w500/2J8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un músico reggae en Kingston.", "full_synopsis": "Ivanhoe Martin llega a Kingston buscando éxito como cantante. Cuando es explotado por un productor de discos, se convierte en un forajido que canta sobre su propia vida.", "director": "Perry Henzell", "cast": ["Jimmy Cliff", "Janet Bartley", "Radwan", "Ralph Brown"], "awards": "Ganó 1 award internacional", "rating": 7.0, "genre": "Reggae"},
        {"id": "reggae_002", "title": "Bob Marley: One Love", "year": 2024, "image": "https://image.tmdb.org/t/p/w500/3J9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La historia de Bob Marley.", "full_synopsis": "La historia del legendario músico Bob Marley, desde sus humildes inicios en Jamaica hasta convertirse en una figura mundial de paz, amor y unidad a través de su música.", "director": "Reinaldo Marcus Green", "cast": ["Khalid", "Michael Ward", "Lashana Lynch", "Giancarlo Esposito"], "awards": "Estreno reciente", "rating": 6.8, "genre": "Reggae"},
        {"id": "reggae_003", "title": "Rockers", "year": 1978, "image": "https://image.tmdb.org/t/p/w500/4J0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Músicos de reggae en Jamaica.", "full_synopsis": "Una comedia que sigue a un grupo de músicos de reggae en Jamaica mientras intentan organizar una fiesta para beneficiar a sus familias y comunidades.", "director": "Kurtis O'Brien", "cast": ["Burning Spear", "Gregory Isaacs", "Eddie Grant", "Nusrat"], "awards": "Festival de cine de Jamaica", "rating": 6.8, "genre": "Reggae"},
        {"id": "reggae_004", "title": "Countryman", "year": 1982, "image": "https://image.tmdb.org/t/p/w500/5K1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un fisherman jamaicano.", "full_synopsis": "Countryman es un fisherman jamaicano que vive una vida pacífica hasta que su barco rescata a dos revolucionarios perseguidos. Su mundo cambia cuando las autoridades lo persiguen.", "director": "Joe Sino", "cast": ["Countryman", "Jennifer", "Minister", "Captain"], "awards": "Nominado a 1 award de independiente", "rating": 6.2, "genre": "Reggae"},
        {"id": "reggae_005", "title": "Shottas", "year": 2002, "image": "https://image.tmdb.org/t/p/w500/7L3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Dos jóvenes jamaicanos.", "full_synopsis": "Dos jóvenes jamaicanos emigran a Miami y se involucran en el crimen organizado. La película explora su rise en el mundo del tráfico de drogas y las consecuencias de sus acciones.", "director": "Terry Wong", "cast": ["Ky-Mani Marley", "Paul Campbell", "Louie Rankin", "Wayne L. Johnson"], "awards": "Nominado a 1 Image Award", "rating": 6.3, "genre": "Reggae"},
        {"id": "reggae_006", "title": "Third World Cop", "year": 1997, "image": "https://image.tmdb.org/t/p/w500/8K3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un oficial de policía en Jamaica.", "full_synopsis": "Un oficial de policía en Jamaica debe arrestar a su viejo amigo criminal cuando este regresa a la isla. La película explora la amistad, la lealtad y la corrupción.", "director": "Rick Elgood", "cast": ["Mark Danvers", "Loudon", "Zoot", "Captain"], "awards": "Nominado a 1 award de caribe", "rating": 5.9, "genre": "Reggae"},
        {"id": "reggae_007", "title": "Blood In Blood Out", "year": 1993, "image": "https://image.tmdb.org/t/p/w500/9L4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Tres primos mexicanos estadounidenses.", "full_synopsis": "La vida de tres primos mexicanos estadounidenses y sus diferentes caminos en Los Ángeles. Uno se une a una banda, otro se convierte en artista, y el tercero lucha contra las adicciones.", "director": "Taylor Hackford", "cast": ["Damian", "Jesse", "Pablo", "Family"], "awards": "Ganó 1 Image Award", "rating": 7.8, "genre": "Reggae"},
        {"id": "reggae_008", "title": "Marley", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/1N6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Documental sobre Bob Marley.", "full_synopsis": "Un documental exhaustivo sobre la vida, música y filosofía de Bob Marley. Incluye entrevistas con familiares, amigos y colaboradores, junto con material de archivo nunca antes visto.", "director": "Kevin Macdonald", "cast": ["Bob Marley", "Rita Marley", "Ziggy Marley", "Chris Blackwell"], "awards": "Ganó 1 Grammy Award", "rating": 7.7, "genre": "Reggae"},
        {"id": "reggae_009", "title": "The Legend of Billie Jean", "year": 1985, "image": "https://image.tmdb.org/t/p/w500/6K2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una adolescente contra la ley.", "full_synopsis": "Billie Jean es una adolescente cuya vida cambia cuando un video de ella se vuelve viral (según la época, un video cassette o una grabación de televisión). Ella huye de las autoridades mientras se convierte en un símbolo de rebeldía.", "director": "Matthew", "cast": ["Helen", "Billie Jean", "Law", "Authority"], "awards": "Nominado a 1 Razzie", "rating": 5.1, "genre": "Reggae"},
        {"id": "reggae_010", "title": "Quierra", "year": 2024, "image": "https://image.tmdb.org/t/p/w500/0M5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Documental sobre la cultura reggae.", "full_synopsis": "Un documental sobre la cultura reggae en Cuba y sus conexiones con Jamaica. Explora cómo el reggae llegó a Cuba y cómo se ha fusionado con la música local.", "director": "Carlos", "cast": ["Músicos cubanos", "Músicos jamaicanos", "Expertos", "Historia"], "awards": "Próximo estreno", "rating": "N/A", "genre": "Reggae"}
    ],
    "Metal": [
        {"id": "metal_001", "title": "This Is It", "year": 2009, "image": "https://image.tmdb.org/t/p/w500/4D5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Michael Jackson rehearsa.", "full_synopsis": "Este documental muestra los ensayos y preparación de Michael Jackson para su serie de conciertos 'This Is It' que debían realizarse en Londres. Filmado entre marzo y junio de 2009.", "director": "Kenny Ortega", "cast": ["Michael Jackson"], "awards": "Nominado a 1 Grammy", "rating": 7.2, "genre": "Metal"},
        {"id": "metal_002", "title": "Metal: A Headbanger's Journey", "year": 2005, "image": "https://image.tmdb.org/t/p/w500/5H6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Documental sobre el heavy metal.", "full_synopsis": "Un documental que explora la cultura y los subgéneros del heavy metal. El director, un fanático del metal, viaja por el mundo entrevistando a músicos, científicos y sociólogos.", "director": "Sam Dunn", "cast": ["Sam Dunn", "Ronnie James Dio", "Tom Araya", "Rob Halford"], "awards": "Ganó 1 award de documental", "rating": 8.0, "genre": "Metal"},
        {"id": "metal_003", "title": "Some Kind of Monster", "year": 2004, "image": "https://image.tmdb.org/t/p/w500/6H7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "La grabación de Metallica.", "full_synopsis": "Este documental sigue a Metallica durante la grabación de su álbum 'St. Anger'. Muestra la terapia de banda que realizaron para superar la departure de su baixista Jason Newsted.", "director": "Bruce Sinofsky", "cast": ["James Hetfield", "Lars Ulrich", "Kirk Hammett", "Robert Trujillo"], "awards": "Nominado a 1 Grammy", "rating": 7.5, "genre": "Metal"},
        {"id": "metal_004", "title": "The Devil's Carnival", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/7I8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un hombre en el infierno.", "full_synopsis": "Un hombre es condenado a un infierno donde los demonios actúan como Payasos en un macabro carnaval. Una mezcla de terror y musical que satiriza la cultura del heavy metal.", "director": "Darren Lynn Bousman", "cast": ["Sean Patrick Flanery", "Briana Evigan", "Paul Sorvino", "Bill Moseley"], "awards": "Festival de terror", "rating": 5.7, "genre": "Metal"},
        {"id": "metal_005", "title": "Bohemian Rhapsody", "year": 2018, "image": "https://image.tmdb.org/t/p/w500/lZAP2R0K30lK2h0Z7p4r1q7b0Z9.jpg", "short_desc": "La historia de Freddie Mercury.", "full_synopsis": "La historia de Freddie Mercury y Queen, desde sus inicios hasta el legendario Live Aid en 1985. Una celebración del genio musical y la legado de una de las bandas más grandes.", "director": "Bryan Singer", "cast": ["Rami Malek", "Ben Hardy", "Gwilym Lee", "Joe Mazzello"], "awards": "Ganó 4 Oscars", "rating": 7.9, "genre": "Metal"},
        {"id": "metal_006", "title": "Rock Star", "year": 2001, "image": "https://image.tmdb.org/t/p/w500/8J9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un cover singer se vuelve famoso.", "full_synopsis": "Chris Cole es el cantante de una banda cover de Steel Dragon. Cuando el cantante original deja la banda, Chris obtiene la oportunidad de sustituirlo, pero debe decidir si vale la pena el sacrifice.", "director": "Stephen Herek", "cast": ["Mark Wahlberg", "Jennifer Aniston", "Dominic West", "Jason Bonham"], "awards": "Nominado a 1 Razzie", "rating": 4.9, "genre": "Metal"},
        {"id": "metal_007", "title": "Wayne's World", "year": 1992, "image": "https://image.tmdb.org/t/p/w500/2J2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Dos amigos presentando un programa.", "full_synopsis": "Wayne y Garth, dos amigos que presentan un programa de TV por cable, luchan por salvar su estadio local de ser vendido a una corporación. Una comedia clásica del rock and roll.", "director": "Penelope Spheeris", "cast": ["Mike Myers", "Dana Carvey", "Tia Carrere", "Lara Flynn Boyle"], "awards": "Nominado a 1 MTV Movie Award", "rating": 7.0, "genre": "Metal"},
        {"id": "metal_008", "title": "Airheads", "year": 1994, "image": "https://image.tmdb.org/t/p/w500/3J3G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una banda de rock.", "full_synopsis": "Una banda de rock llamada The Lone Rangers está tratando de conseguir un contrato discográfico. Cuando toman una estación de radio como rehén para reproducir su demo, las cosas se complican.", "director": "Adam McKay", "cast": ["Brendan Fraser", "Steve Buscemi", "Adam Sandler", "Jenna Elfman"], "awards": "Nominado a 1 Razzie", "rating": 5.8, "genre": "Metal"},
        {"id": "metal_009", "title": "Black Sabbath: The End", "year": 2024, "image": "https://image.tmdb.org/t/p/w500/1I1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Documental sobre Black Sabbath.", "full_synopsis": "Un documental sobre la gira de despedida de Black Sabbath, la banda pionera del heavy metal. La gira final de Ozzy Osbourne, Tony Iommi y Geezer Butler.", "director": "", "cast": ["Ozzy Osbourne", "Tony Iommi", "Geezer Butler"], "awards": "Próximo estreno", "rating": "N/A", "genre": "Metal"},
        {"id": "metal_010", "title": "Twisted Sister: We Are Twisted Fucking Sister", "year": 2014, "image": "https://image.tmdb.org/t/p/w500/0H0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Documental sobre Twisted Sister.", "full_synopsis": "Un documental sobre la legendaria banda de glam metal Twisted Sister. Desde sus inicios en los años 70 hasta su éxito con 'We're Not Gonna Take It'.", "director": "Andrew Horn", "cast": ["Dee Snider", "Eddie Ojeda", "Jay Jay French", "Mark Mendoza"], "awards": "Ganó 1 award de documental", "rating": 7.6, "genre": "Metal"}
    ],
    "Indie": [
        {"id": "indie_001", "title": "Garden State", "year": 2004, "image": "https://image.tmdb.org/t/p/w500/4J4G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un actor regresa a su ciudad natal.", "full_synopsis": "Andrew Largeman, un actor que ha estado medicado durante años, regresa a su ciudad natal en Nueva Jersey después de que su madre muere. Conoce a una extraña joven que lo ayuda a descubrir la vida real.", "director": "Zach Braff", "cast": ["Zach Braff", "Natalie Portman", "Peter Sarsgaard", "Ian Holm"], "awards": "Ganó 1 Grammy - Mejor Banda Sonora Original", "rating": 7.3, "genre": "Indie"},
        {"id": "indie_002", "title": "Nick and Norah's Infinite Playlist", "year": 2008, "image": "https://image.tmdb.org/t/p/w500/5K5G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una noche en Nueva York.", "full_synopsis": "Nick y Norah, dos estudiantes universitarios, se conocen en un club de punk. Esa noche, vagan por Nueva York buscando una banda misteriosa mientras desarrollan una conexión.", "director": "Peter Sollett", "cast": ["Michael Cera", "Kat Dennings", "Aaron Yoo", "Ari Graynor"], "awards": "Nominado a 1 Independent Spirit Award", "rating": 6.7, "genre": "Indie"},
        {"id": "indie_003", "title": "Submarine", "year": 2010, "image": "https://image.tmdb.org/t/p/w500/6K6G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un adolescente excéntrico.", "full_synopsis": "Oliver Tate es un adolescente excéntrico de 15 años que tiene dos misiones: evitar que su madre abandone a su padre y perder su virginidad con su compañera de clase. Una comedia dramática dulce y única.", "director": "Richard Ayoade", "cast": ["Craig Roberts", "Sally Hawkins", "Paddy Considine", "Yasmin Paige"], "awards": "Nominado a 1 BAFTA", "rating": 7.0, "genre": "Indie"},
        {"id": "indie_004", "title": "The Perks of Being a Wallflower", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/7K7G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un adolescente solitario.", "full_synopsis": "Charlie, un adolescente solitario, encuentra amigos y amor cuando dos hermanos mayores lo aceptan en su grupo. La película explora temas de amistad, amor, trauma y crecimiento.", "director": "Stephen Chbosky", "cast": ["Logan Lerman", "Emma Watson", "Ezra Miller", "Mae Whitman"], "awards": "Nominado a 3 People's Choice Awards", "rating": 7.9, "genre": "Indie"},
        {"id": "indie_005", "title": "Eternal Sunshine of the Spotless Mind", "year": 2004, "image": "https://image.tmdb.org/t/p/w500/8K8G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un hombre borra a su ex de su memoria.", "full_synopsis": "Joel se entera de que Clementine, su novia, ha borrado todos los recuerdos de él de su mente. Decidido a hacer lo mismo, Joel revive su relación mientras ocurre el borrado.", "director": "Michel Gondry", "cast": ["Jim Carrey", "Kate Winslet", "Kirsten Dunst", "Mark Ruffalo"], "awards": "Ganó 1 Oscar - Mejor Guion Original", "rating": 8.3, "genre": "Indie"},
        {"id": "indie_006", "title": "500 Days of Summer", "year": 2009, "image": "https://image.tmdb.org/t/p/w500/9L9G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Los altibajos de una relación.", "full_synopsis": "La historia de Tom y Summer, contada de forma no lineal a través de los 500 días de su relación. Desde el día 1 hasta el final, explorando cómo nos enamoramos y cómo nos decepciones.", "director": "Marc Webb", "cast": ["Joseph Gordon-Levitt", "Zooey Deschanel", "Geoffrey Arend", "Chloe Grace Moretz"], "awards": "Nominado a 1 Golden Globe", "rating": 7.7, "genre": "Indie"},
        {"id": "indie_007", "title": "The Spectacular Now", "year": 2013, "image": "https://image.tmdb.org/t/p/w500/0M0G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un adolescente conoce a una chica.", "full_synopsis": "Sutter Keely es un estudiante despreocupado que vive el momento. Cuando Aimee Finecky, una chica callada, entra en su vida, Sutter debe cuestionar su estilo de vida y enfrentar su pasado.", "director": "James Ponsoldt", "cast": ["Miles Teller", "Shailene Woodley", "Brie Larson", "Masam Holden"], "awards": "Ganó 1 Independent Spirit Award", "rating": 7.1, "genre": "Indie"},
        {"id": "indie_008", "title": "Begin Again", "year": 2013, "image": "https://image.tmdb.org/t/p/w500/6K2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Una ejecutiva y un músico.", "full_synopsis": "Greta, una ejecutiva de discográfica, y Dan, un músico callejero, forman una conexión en Nueva York. Juntos graban un álbum por toda la ciudad, sin usar un estudio de grabación tradicional.", "director": "John Carney", "cast": ["Keira Knightley", "Mark Ruffalo", "Adam Levine", "Hailee Steinfeld"], "awards": "Ganó 1 Oscar - Mejor Canción Original", "rating": 7.4, "genre": "Indie"},
        {"id": "indie_009", "title": "Her", "year": 2013, "image": "https://image.tmdb.org/t/p/w500/1N1G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Un escritor y una IA.", "full_synopsis": "En un futuro cercano, Theodore Twombly, un escritor solitario, compra un sistema operativo de inteligencia artificial llamado Samantha. Desarrollan una relación que desafía los límites entre humano y máquina.", "director": "Spike Jonze", "cast": ["Joaquin Phoenix", "Scarlett Johansson", "Amy Adams", "Rooney Mara"], "awards": "Ganó 1 Oscar - Mejor Guion Original", "rating": 8.0, "genre": "Indie"},
        {"id": "indie_010", "title": "Moonrise Kingdom", "year": 2012, "image": "https://image.tmdb.org/t/p/w500/2J2G5G5G5G5G5G5G5G5G5G5G5G.jpg", "short_desc": "Dos niños huyen juntos.", "full_synopsis": "En 1965 en Nueva Inglaterra, dos niños de 12 años, Sam y Suzy, huyen juntos. Una búsqueda en toda la isla comienza mientras los adultos intentan encontrarlos.", "director": "Wes Anderson", "cast": ["Jared Gilman", "Kara Hayward", "Bruce Willis", "Edward Norton"], "awards": "Nominado a 1 Oscar - Mejor Guion Original", "rating": 7.8, "genre": "Indie"}
    ]
}

def classify_mood(acousticness, danceability, energy, speechiness, valence, tempo):
    scores = {
        'happy': 0, 'sad': 0, 'energetic': 0, 'calm': 0, 'tense': 0,
        'romantic': 0, 'nostalgic': 0, 'confident': 0, 'melancholic': 0,
        'euphoric': 0, 'bored': 0, 'aggressive': 0, 'dreamy': 0,
        'mysterious': 0, 'playful': 0
    }
    
    scores['happy'] = (valence * 0.4) + (energy * 0.3) + (danceability * 0.3)
    scores['sad'] = ((1 - valence) * 0.4) + ((1 - energy) * 0.3) + (acousticness * 0.2)
    scores['energetic'] = (energy * 0.4) + (tempo / 200 * 0.3) + (danceability * 0.3)
    scores['calm'] = ((1 - energy) * 0.4) + (acousticness * 0.3) + ((1 - speechiness) * 0.2)
    scores['tense'] = ((1 - danceability) * 0.3) + ((1 - valence) * 0.3) + (energy * 0.3)
    scores['romantic'] = (valence * 0.4) + ((1 - energy) * 0.3) + ((1 - danceability) * 0.2)
    scores['nostalgic'] = (acousticness * 0.5) + ((1 - energy) * 0.3) + (valence * 0.2)
    scores['confident'] = (energy * 0.4) + (valence * 0.3) + (danceability * 0.3)
    scores['melancholic'] = (acousticness * 0.3) + ((1 - valence) * 0.4) + ((1 - energy) * 0.3)
    scores['euphoric'] = (energy * 0.35) + (valence * 0.35) + (danceability * 0.3)
    scores['bored'] = ((1 - energy) * 0.4) + ((1 - valence) * 0.3) + ((1 - danceability) * 0.3)
    scores['aggressive'] = (energy * 0.4) + (speechiness * 0.3) + ((1 - acousticness) * 0.3)
    scores['dreamy'] = (acousticness * 0.4) + ((1 - energy) * 0.3) + ((1 - danceability) * 0.3)
    scores['mysterious'] = (acousticness * 0.4) + ((1 - speechiness) * 0.3) + ((1 - valence) * 0.2)
    scores['playful'] = (danceability * 0.4) + (valence * 0.3) + (energy * 0.3)
    
    for mood in scores:
        scores[mood] = min(scores[mood] * 100, 100)
    
    return scores

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

def get_movie_recommendations(user_genres):
    recommendations = {}
    
    for genre in user_genres:
        matched_movies = []
        
        for db_genre, movies in MOVIE_DATABASE.items():
            if db_genre.lower() == genre.lower():
                matched_movies = movies
                break
            elif genre.lower() in db_genre.lower() or db_genre.lower() in genre.lower():
                if len(matched_movies) == 0:
                    matched_movies = movies
        
        if len(matched_movies) == 0:
            matched_movies = MOVIE_DATABASE["Indie"]
        
        recommendations[genre] = matched_movies[:10]
    
    return recommendations

def get_audio_features_safe(sp, track_ids):
    if not track_ids:
        return None
    
    try:
        batch_size = 50
        all_features = []
        
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i + batch_size]
            logger.info(f"Solicitando audio-features para lote {i//batch_size + 1}")
            features = sp.audio_features(tracks=batch)
            all_features.extend(features)
        
        return all_features
        
    except SpotifyException as e:
        logger.error(f"Spotify API Error: HTTP {e.http_status} - {e.msg}")
        return None
    except Exception as e:
        logger.error(f"Error general al obtener audio-features: {e}")
        return None

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
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope='user-top-read'
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope='user-top-read'
    )
    
    try:
        logger.info("Iniciando proceso de autenticación...")
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info['access_token']
        
        sp = spotipy.Spotify(auth=access_token)
        
        user = sp.current_user()
        user_name = user['display_name']
        logger.info(f"Usuario autenticado: {user_name}")
        
        top_genres = get_top_genres(sp)
        logger.info(f"Géneros principales: {top_genres}")
        
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
        track_ids = [track['id'] for track in top_tracks['items']]
        logger.info(f"Tracks obtenidos: {len(track_ids)}")
        
        audio_features = get_audio_features_safe(sp, track_ids)
        
        averages = {
            'acousticness': 0.5, 'danceability': 0.5, 'energy': 0.5,
            'speechiness': 0.1, 'valence': 0.5, 'tempo': 120, 'instrumentalness': 0.1
        }
        api_error = False
        
        if audio_features:
            feature_sums = {
                'acousticness': 0, 'danceability': 0, 'energy': 0,
                'speechiness': 0, 'valence': 0, 'tempo': 0, 'instrumentalness': 0
            }
            
            valid_tracks = 0
            for af in audio_features:
                if af:
                    for feature in feature_sums:
                        feature_sums[feature] += af[feature]
                    valid_tracks += 1
            
            if valid_tracks > 0:
                averages = {feature: value / valid_tracks for feature, value in feature_sums.items()}
            else:
                api_error = True
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

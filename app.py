import logging
import os
import sys
import warnings
import threading
import re
import jwt
import socket

from uuid import uuid4
from flask import Flask, request, render_template, send_from_directory, jsonify, send_file, Response, abort, redirect, url_for, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from waitress import serve
from datetime import timedelta, datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()

# dir modules
from database_utils import DB, create_localdb, update_id
from library_manager import sync_libraries, create_settings, load_settings
from tmdb_client import TMDBClient


logging.basicConfig(
    filename='logs.log', 
    encoding='utf-8', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logger = logging.getLogger(__name__)



flask_key = os.getenv('FLASK_KEY')
if not flask_key:
    logger.critical("Missing FLASK_KEY in environment. Cannot start the app.")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = flask_key
app.config.update(
    PERMANENT_SESSION_LIFETIME = timedelta(days=182),
    SESSION_COOKIE_SECURE = False, 
    SESSION_COOKIE_HTTPONLY = True, 
    SESSION_COOKIE_SAMESITE = 'Lax'
)



warnings.filterwarnings("ignore", category=UserWarning, module="flask_limiter") # supress "Using the in-memory storage for tracking rate limits as no storage"
limiter = Limiter(get_remote_address, app=app, default_limits=[])
tight_rate, default_rate, loose_rate = '30/minute', '60/minute', '120/minute'







## AUTH WRAPPERS
## AUTH WRAPPERS
## AUTH WRAPPERS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('auth'):
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated_function


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({'error': 'invalid_auth_token'}), 401

        token = auth_header.split(" ")[1]

        try:
            token = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'invalid_auth_token'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'invalid_auth_token'}), 401

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'unauthorized'}), 401

        return f(*args, **kwargs)
    return decorated_function






## TOKEN
## TOKEN
## TOKEN

# short-lived token
def generate_token():
    payload = {
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1)
    }
    token = jwt.encode(payload, app.secret_key, algorithm="HS256")
    return token


@app.route("/auth/v1/token", methods=["GET"])
def auth_token():
    if not session.get("auth"):
        return jsonify({"error": "not_logged_in"}), 401
    
    token = generate_token()
    return jsonify({'access_token': token, 'expires_in': 60})


jobs = {}  # temp in-memory job store
@app.route('/status/v1/<job_id>', methods=['GET'])
@token_required
def check_job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'job not found'}), 404
    return jsonify(job)



@app.route('/rescan', methods=['POST'])
@limiter.limit('1 per 10 minutes')
@login_required
@admin_required
def rescan():
    threading.Thread(target=sync_libraries).start()
    return jsonify({"message": "Rescan started"}), 202

## HTML Endpoints
## HTML Endpoints
## HTML Endpoints

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('15 per 10 minutes')
def login():
    if session.get('auth'):
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        password = request.form['login_key']

        # Check if entered key matches any stored hash
        users = DB.fetch_users()

        for user in users:
            if check_password_hash(user['hash'], password):
                session.permanent = True
                session['auth'] = True
                session['key'] = user['key']
                session['is_admin'] = user['is_admin']
                session['is_adult'] = user['is_adult']

                return redirect(url_for('index'))
        error = "Invalid key"

    return render_template('login.html', error=error)


@app.route('/logout')
@limiter.limit('15 per 10 minutes')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/browse')
@login_required
def browse():
    return render_template('browse.html')

@app.route('/<int:item_id>')
@login_required
def item_page(item_id):
    return render_template('title.html')


@app.route('/<int:item_id>/watch/<int:video_id>')
@login_required
def watch_page(item_id, video_id):
    return render_template('video.html')


@app.route('/404')
@login_required
def not_found_page():
    abort(404)


@app.errorhandler(404)
@login_required
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(429)
@login_required
def ratelimit_handler(e):
    return render_template('429.html'), 429





## API CONTENT Endpoints
## API CONTENT Endpoints
## API CONTENT Endpoints
@app.route('/content/v1/index')
@token_required
def get_index(): 
    try:
        index = DB.fetch_catalog_index()
    except Exception as e:
        logger.error(f'failed to fetch index, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400

    library = dict()
    for id, title, category in index:
        letter = title[0]

        if letter not in library:
            library[letter] = [{'id': id, 'title': title, 'category':category}]
        else:
            library[letter].append({'id': id, 'title': title, 'category':category})

    library = dict(sorted(library.items()))
    for letter in library:
        library[letter].sort(key=lambda x: x['title'])
    return jsonify(library)


@app.route('/content/v1/catalog')
@token_required
def get_catalog(): 
    try:
        catalog = DB.fetch_catalog(order_by='entry_updated', limit=50)
    except Exception as e:
        logger.error(f'failed to fetch catalog, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    
    data = [{'id': item.id, 
             'media_type': item.media_type,
             'tmdb': item.tmdb_id,
             'title': item.title,
             'original_title': item.original_title,
             'release_date': item.release_date,
             'poster_path': item.poster_path,
             'entry_updated': item.entry_updated,
             'newest_video': item.new_video_inserted
             } for item in catalog]
    data = sorted(data, key=lambda k:k['newest_video'], reverse=True)
    return jsonify(data)


@app.route('/content/v1/tv')
@token_required
def get_catalog_tv():
    try:
        catalog = DB.fetch_catalog(order_by='entry_updated', media_type='tv')
    except Exception as e:
        logger.error(f'failed to fetch tv catalog, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    
    data = [{'id': item.id, 
             'media_type': item.media_type,
             'tmdb': item.tmdb_id,
             'title': item.title,
             'original_title': item.original_title,
             'release_date': item.release_date,
             'poster_path': item.poster_path,
             'entry_updated': item.entry_updated,
             'newest_video': item.new_video_inserted
             } for item in catalog]
    data = sorted(data, key=lambda k:k['newest_video'], reverse=True)
    return jsonify(data)


@app.route('/content/v1/movies')
@token_required
def get_catalog_movies():
    try:
        catalog = DB.fetch_catalog(order_by='entry_updated', media_type='movie')
    except Exception as e:
        logger.error(f'failed to fetch movies catalog, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
        
    data = [{'id': item.id, 
             'media_type': item.media_type,
             'tmdb': item.tmdb_id,
             'title': item.title,
             'original_title': item.original_title,
             'release_date': item.release_date,
             'poster_path': item.poster_path,
             'entry_updated': item.entry_updated,
             'newest_video': item.new_video_inserted
             } for item in catalog]
    data = sorted(data, key=lambda k:k['newest_video'], reverse=True)
    return jsonify(data)


@app.route('/content/v1/item/<int:item_id>')
@token_required
def get_item(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400
    

    
    try:
        item = DB.fetch_id(item_id)
    except Exception as e:
        logger.error(f'failed to fetch item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400

    if item and item.media_type == 'movie':
        item_ = DB.fetch_movie_details(item_id)  # refresh item.movie_details
        data = {
            "id": item.id,
            "media_type": item.media_type,
            "tmdb_id": item.tmdb_id,
            "title": item.title,
            "original_title": item.original_title,
            "release_date": item.release_date,
            "tagline": item.tagline,
            "overview": item.overview,
            "backdrop_path": item.backdrop_path,
            "poster_path": item.poster_path,
            "homepage": item.homepage,
            "popularity": item.popularity,
            "vote_average": item.vote_average,
            "vote_count": item.vote_count,
            "status": item.status,
            "entry_updated": item.entry_updated,
            "genres": [g.name for g in item.genres],
            "logos": [{'lang': l.lang, 'file_path': l.file_path} for l in item.logos],

            "budget": item_.movie_details.budget if item_.movie_details else None,
            "revenue": item_.movie_details.revenue if item_.movie_details else None,
            "runtime": item_.movie_details.runtime if item_.movie_details else None
        }
        return jsonify(data)
    
    elif item and item.media_type == 'tv':
        item_ = DB.fetch_tv_details(item_id)
        episodes = DB.fetch_episodes(item_id)
        
        today = datetime.today().date()
        future_eps = [ep for ep in episodes if datetime.strptime(ep.air_date, "%Y-%m-%d").date() > today]
        
        next_episode = min(future_eps, key=lambda ep: datetime.strptime(ep.air_date, "%Y-%m-%d")) if future_eps else None
        next_ep_data = {'air_date': next_episode.air_date, 
                        'season_number': next_episode.season_number, 
                        'episode_number': next_episode.episode_number,
                        'name': next_episode.name} if next_episode else {}
        data = {
            "id": item.id,
            "media_type": item.media_type,
            "tmdb_id": item.tmdb_id,
            "title": item.title,
            "original_title": item.original_title,
            "release_date": item.release_date,
            "tagline": item.tagline,
            "overview": item.overview,
            "backdrop_path": item.backdrop_path,
            "poster_path": item.poster_path,
            "homepage": item.homepage,
            "popularity": item.popularity,
            "vote_average": item.vote_average,
            "vote_count": item.vote_count,
            "status": item.status,
            "entry_created": item.entry_created,
            "entry_updated": item.entry_updated,
            "genres": [g.name for g in item.genres],
            "logos": [{'lang': l.lang, 'file_path': l.file_path} for l in item.logos],

            "next_episode": next_ep_data,
            "first_air_date": item_.tv_details.first_air_date if item_.tv_details else None,
            "last_air_date": item_.tv_details.last_air_date if item_.tv_details else None,
            "number_of_seasons": item_.tv_details.number_of_seasons if item_.tv_details else None,
            "number_of_episodes": item_.tv_details.number_of_episodes if item_.tv_details else None
        }
        return jsonify(data)
    
    else:
        return jsonify({"error": "Item not found"}), 404


@app.route('/content/v1/item/<int:item_id>/genres')
@token_required
def get_item_genres(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        genres = DB.fetch_genres(item_id)
    except Exception as e:
        logger.error(f'failed to fetch genres for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    
    if not genres:
        return jsonify({"error": "item not found"}), 404
    
    return jsonify([{"id": g.id, "name": g.name} for g in genres])


@app.route('/content/v1/item/<int:item_id>/ratings')
@token_required
def get_item_ratings(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        ratings = DB.fetch_ratings(item_id)
    except Exception as e:
        logger.warning(f'failed to fetch ratings for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    
    if not ratings:
        return jsonify({"error": "item not found"}), 404
    
    return jsonify([{"id": r.id, "rating": r.rating, "country": r.country} for r in ratings])


@app.route('/content/v1/item/<int:item_id>/cast')
@token_required
def get_item_cast(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        cast_list = DB.fetch_cast(item_id)
    except Exception as e:
        logger.error(f'failed to fetch cast for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
        
    if not cast_list:
        return jsonify({"error": "item not found"}), 404
    
    actor_map = {}
    for cast in cast_list:
        actor = cast.actor
        character = cast.character

        actor_id = actor.id
        if actor_id not in actor_map:
            actor_map[actor_id] = {"id": actor.id,
                                    "tmdb_id": actor.tmdb_id,
                                    "gender": actor.gender,
                                    "known_for_department": actor.known_for_department,
                                    "name": actor.name,
                                    "original_name": actor.original_name,
                                    "popularity": actor.popularity,
                                    "profile_path": actor.profile_path,
                                    "entry_updated": actor.entry_updated,
                                    "characters": [],
                                    "episode_count": 0}
            
        char_dict = {"id": character.id,
                        "character": character.character}
    
        if char_dict not in actor_map[actor_id]["characters"]:
            actor_map[actor_id]["characters"].append(char_dict)

        actor_map[actor_id]["episode_count"] += cast.episode_count or 0

    return jsonify(list(actor_map.values()))


@app.route('/content/v1/item/<int:item_id>/trailers')
@token_required
def get_item_trailers(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        trailers = DB.fetch_trailers(item_id)
    except Exception as e:
        logger.error(f'failed to fetch trailers for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
        
    if not trailers:
        return jsonify({"error": "item not found"}), 404
    
    return jsonify([{"id": v.id,
                        "title": v.title,
                        "key": v.key,
                        "site": v.site,
                        "type": v.type,
                        "official": v.official,
                        "published_at": v.published_at,
                        "lang": v.lang,
                        "entry_updated": v.entry_updated
                        } for v in trailers])


@app.route('/content/v1/item/<int:item_id>/networks')
@token_required
def get_item_networks(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        networks = DB.fetch_networks(item_id)
    except Exception as e:
        logger.error(f'failed to fetch networks for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
        
    if not networks:
        return jsonify({"error": "item not found"}), 404
    
    return jsonify([{"id": n.id,
                        "name": n.name,
                        "logo_path": n.logo_path,
                        "origin_country": n.origin_country
                        } for n in networks])


@app.route('/content/v1/item/<int:item_id>/seasons')
@token_required
def get_item_seasons(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        seasons = DB.fetch_season(item_id)
    except Exception as e:
        logger.error(f'failed to fetch seasons for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
        
    if not seasons:
        return jsonify({"error": "item not found"}), 404
    
    result = []
    for s in seasons:
        season_data = {
            "season_number": s.season_number,
            "name": s.name,
            "overview": s.overview,
            "poster_path": s.poster_path,
            "episode_count": s.episode_count,
            "episodes": [{
                "id": e.id,
                "media_id": e.media_id,
                "season_id": e.season_id,
                "season_number": e.season_number,
                "episode_number": e.episode_number,
                "name": e.name,
                "episode_type": e.episode_type,
                "overview": e.overview,
                "air_date": e.air_date,
                "still_path": e.still_path,
                "runtime": e.runtime,
                "vote_average": e.vote_average,
                "vote_count": e.vote_count
                } for e in s.episodes]
        }
        result.append(season_data)

    return jsonify(result)


@app.route('/content/v1/item/<int:item_id>/episodes')
@token_required
def get_item_episodes(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        episodes = DB.fetch_episodes(item_id)
    except Exception as e:
        logger.error(f'failed to fetch episodes for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
            
    if not episodes:
        return jsonify({"error": "item not found"}), 404
    
    return jsonify([{
        "id": e.id,
        "media_id": e.media_id,
        "season_id": e.season_id,
        "season_number": e.season_number,
        "episode_number": e.episode_number,
        "name": e.name,
        "episode_type": e.episode_type,
        "overview": e.overview,
        "air_date": e.air_date,
        "still_path": e.still_path,
        "runtime": e.runtime,
        "vote_average": e.vote_average,
        "vote_count": e.vote_count
        } for e in episodes])


@app.route('/content/v1/item/<int:item_id>/videos')
@token_required
def get_videos(item_id):
    if not item_id or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400



    try:
        videos = DB.fetch_videos(item_id)
    except Exception as e:
        logger.error(f'failed to fetch videos for item (ID {item_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
            
    if not videos:
        return jsonify({"error": "item not found"}), 404

    # Preload all episodes for this item and map by (season_number, episode_number)
    episodes = DB.fetch_episodes(item_id)
    episode_map = {
        (ep.season_number, ep.episode_number): ep for ep in episodes
    }

    result = []
    for v in videos:
        # Basic metadata
        metadata = {
            "key_frame": v.keyframe_path,
            "resolution": v.resolution,
            "extension": v.extension,
            "audio_codec": v.audio_codec,
            "video_codec": v.video_codec,
            "duration": v.duration,
            "frame_rate": v.frame_rate,
            "width": v.width,
            "height": v.height,
            "aspect_ratio": v.aspect_ratio,
        }

        # Subtitles
        subtitles = [{
            "id": s.id,
            "lang": s.lang,
            "label": s.label,
        } for s in v.subtitles]

        video_data = {
            "id": v.id,
            "media_id": v.media_id,
            "season_number": v.season_number,
            "episode_number": v.episode_number,
            "metadata": metadata,
            "subtitles": subtitles,
        }

        # Add episode data if it exists
        if v.season_number and v.episode_number:
            ep = episode_map.get((v.season_number, v.episode_number))
            if ep:
                video_data.update({
                    "air_date": ep.air_date,
                    "episode_type": ep.episode_type,
                    "name": ep.name,
                    "overview": ep.overview,
                    "runtime": ep.runtime,
                    "still_path": ep.still_path,
                    "vote_average": ep.vote_average,
                    "vote_count": ep.vote_count
                })

        result.append(video_data)

    return jsonify(result)


@app.route('/content/v1/video/<int:video_id>')
@token_required
def get_video(video_id):
    if not video_id or not isinstance(video_id, int) or video_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400  
      


    try:  
        video = DB.fetch_video(video_id)
    except Exception as e:
        logger.error(f'failed to fetch video (ID {video_id}), exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    
    if not video:
        return jsonify({"error": "item not found"}), 404
    

    metadata = {
        "key_frame": video.keyframe_path,
        "resolution": video.resolution,
        "extension": video.extension,
        "audio_codec": video.audio_codec,
        "video_codec": video.video_codec,
        "duration": video.duration,
        "frame_rate": video.frame_rate,
        "width": video.width,
        "height": video.height,
        "aspect_ratio": video.aspect_ratio,
    }

    data = {
        "id": video.id,
        "media_id": video.media_id,
        "hash_key": video.hash_key,
        "metadata": metadata,
        "subtitles": [{
            "id": s.id,
            "lang": s.lang,
            "label": s.label,
            "hash_key": s.hash_key
        } for s in video.subtitles]
    }

    if video.season_number or video.episode_number:
        episode = DB.fetch_episode(video.media_id, video.season_number, video.episode_number) 
        
        if episode:  
            episode_data = {
                'season_number': video.season_number,
                'episode_number': video.episode_number,
                'air_date': episode.air_date,
                'episode_type':episode.episode_type,
                'name':episode.name,
                'overview':episode.overview,
                'runtime':episode.runtime,
                'still_path':episode.still_path,
                'vote_average':episode.vote_average,
                'vote_count':episode.vote_count
            }   
            data.update(episode_data)
    else:
        moviedets = DB.fetch_id(data.get('media_id'))

        if moviedets:
            extra_d = {
                'name': moviedets.title,

            }
            data.update(extra_d)

    return jsonify(data)


@app.route('/content/v1/video/<int:video_id>/subtitles')
@token_required
def get_video_subtitles(video_id):
    if not video_id or not isinstance(video_id, int) or video_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400  


    try:
        subtitles = DB.fetch_subtitles(video_id)
    except Exception as e:
        logger.error(f'failed to fetch video (ID {video_id}) subtitles, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    
    if not subtitles:
        return jsonify({"error": "item not found"}), 404
    
    return jsonify([{"id": s.id,
                        "media_id": s.media_id,
                        "video_id": s.video_id,
                        "lang": s.lang,
                        "label": s.label,
                        "hash_key": s.hash_key
                        } for s in subtitles])


@app.route('/content/v1/search', methods=['GET'])
@token_required
def search_results():
    query = request.args.get('query', '')
    
    if not query:
         return jsonify({'error': 'invalid query.'}), 400

    if len(query) > 200:
        logger.warning(f'search term too long. ({query})')
        return jsonify({"error": "search term too long"}), 400

    if not re.match(r"^[\w\s\-\']*$", query):
        logger.warning(f'invalid search term. ({query})')
        return jsonify({"error": "invalid search term"}), 400
    


    safer_string = query.replace('%', r'\%').replace('_', r'\_')
    if safer_string:
        try:
            results = DB.search(safer_string)
        except Exception as e:
            logger.error(f'failed to search for {safer_string}, exception {e}.', exc_info=True)
            return jsonify([{'error': 'internal error.'}]), 400   
                 
        data = [{'id': item.id, 
                'media_type': item.media_type,
                'tmdb': item.tmdb_id,
                'title': item.title,
                'original_title': item.original_title,
                'release_date': item.release_date,
                'poster_path': item.poster_path,
                'entry_updated': item.entry_updated,
                'genres': [g.name for g in item.genres]
                } for item in results]
    return jsonify(results=data)






# API ACCOUNTS Endpoints
# API ACCOUNTS Endpoints
# API ACCOUNTS Endpoints

@app.route('/accounts/v1/me')
@token_required
def get_user_profile():
    key = session.get('key')

    if not key or not isinstance(key, str):
        return jsonify({'error': 'invalid session key'}), 400
    
    

    try:
        user = DB.fetch_user(key)
        profile_name = user.user_profile.profile_name
        profile_picture = user.user_profile.profile_picture
    except Exception as e:
        logger.error(f'failed to load profile name. redirecting to logout in attempt to clean cache. error -> {e}', exc_info=True)
        return jsonify({'error': 'failed to load user profile.'})



    
    return jsonify({'profile': profile_name, 'profile_picture': profile_picture})


@app.route('/accounts/v1/p')
@token_required
def get_user_video_playback():
    key = session.get('key')
    video_id = request.args.get('v', type=int)

    if not key or not isinstance(key, str):
        return jsonify({'error': 'invalid session key'}), 400

    if not video_id or not isinstance(video_id, int) or video_id <= 0:
        return jsonify({'error': 'invalid data.'}), 400  



    try:
        user = DB.fetch_user(key)
        playback = user.user_playback
    except Exception as e:
        logger.error(f'failed to load user.playback, error -> {e}', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400

    watched = False
    video_start_time = 0
    for video in playback:
        if key == video.user_key and video_id == video.video_id:
            watched = video.watched
            video_start_time = video.paused_at
            break

    return jsonify({'watched': watched, 'video_start_time': video_start_time})


@app.route('/accounts/v1/w', methods=['POST'])
@token_required
def post_user_watchtime():
    key = session.get('key')
    data = request.get_json()

    media_id = data.get('media_id')
    video_id = data.get('video_id')
    paused_at = data.get('pausedAt', 0)
    seconds_played = data.get('secondsPlayed', 0)
    video_duration = data.get('videoDuration', 0)

    if not key or not isinstance(key, str):
        logger.warning(f'endpoint "/accounts/v1/w" session KEY not found. ({key})')
        return jsonify({'error': 'session KEY not found.'}), 400    
    
    if not data:
        logger.warning(f'endpoint "/accounts/v1/w" recieved invalid data. ({data})')
        return jsonify({'error': 'missing JSON data'}), 400
    
    if not all([video_id, media_id]):
        logger.warning(f'endpoint "/accounts/v1/w" recieved invalid data. ({data})')
        return jsonify({'error': 'invalid data. (!)'}), 400
    
    if not isinstance(media_id, int) or not isinstance(video_id, int) or not isinstance(paused_at, int) or not isinstance(video_duration, int):
        logger.warning(f'endpoint "/accounts/v1/w" recieved invalid data. ({data})')
        return jsonify({'error': 'invalid data.'}), 400



    # Determin if the video is_watched by a user
    # Percentage thresholds
    short_video_percentage = 0.90
    long_video_percentage = 0.85
    # Determine the applicable threshold'
    watched = False
    if video_duration:
        if video_duration < 300:
            threshold = short_video_percentage
        else:
            threshold = long_video_percentage
        # Calculate the threshold time
        if paused_at >= video_duration * threshold:
            watched = True

    try:
        data = {
            'media_id': int(media_id),
            'video_id': int(video_id),
            'video_paused_at': int(paused_at),
            'seconds_played': int(seconds_played),
            'video_duration': int(video_duration),
            'watched': watched 
        }
        DB.set_user_playback(key, data)
    except Exception as e:
        logger.error(f'exception while trying to update user playback. (user: {key}, data: {data}) error -> {e}')
        return jsonify({'error': 'internal error.'}), 400
    
    return jsonify({"message": "watchtime updated successfully."}), 200


@app.route('/accounts/v1/l', methods=['GET', 'POST'])
@token_required
def user_library():
    key = session.get('key')

    if not key or not isinstance(key, str):
        return jsonify({'error': 'invalid session key'}), 400



    if request.method == 'GET':
        id = request.args.get('id', type=int)
        if not id or not isinstance(id, int) or id <= 0:
            return jsonify({'error': 'invalid data.'}), 400  

        try:
            user = DB.fetch_user(key)
            try:
                library = user.user_library
                playback = user.user_playback
            except Exception as e:
                logger.warning(f'failed to load user library, error -> {e}', exc_info=True)
                library = []
                playback = []
        except Exception as e:
            logger.warning(f'failed to load user, error -> {e}', exc_info=True)

        
        rated = 0
        watchlisted = 0

        if library:
            for item in library:
                if item.media_id == id:
                    rated, watchlisted = item.rated, item.watchlisted

        videos = []
        if playback:
            for video in playback:
                if video.media_id == id:
                    videos.append({'video_id': video.video_id, 'watched': video.watched, 'paused_at': video.paused_at})

        data = {
            'rated': rated,
            'watchlisted': watchlisted,
            'videos': videos
        }

        return jsonify(data)
    elif request.method == 'POST':
        data = request.get_json()
        media_id = data.get('media_id', None)
        video_id = data.get('video_id', None)
        
        if not data and not media_id and not isinstance(media_id, int):
            return jsonify({'error': 'invalid payload'}), 400  

        if not video_id:
            watchlisted = data.get('watchlisted') 
            rated = data.get('rated')
            if isinstance(watchlisted, int):
                DB.set_user_library(key, {'media_id': media_id, 'watchlisted': watchlisted})
            if isinstance(rated, int):
                DB.set_user_library(key, {'media_id': media_id, 'rated': rated})
        else:
            if isinstance(video_id, int):
                watched = data.get('watched')

        return jsonify({'message': 'library updated'}), 200


@app.route('/accounts/v1/l/a')
@token_required
def user_library_all():
    key = session.get('key')

    if not key or not isinstance(key, str):
        return jsonify({'error': 'invalid session key'}), 400



    library = []
    playback = []
    try:
        user = DB.fetch_user(key)
        try:
            library = user.user_library
            playback = user.user_playback
        except Exception as e:
            logger.warning(f'failed to load user library, error -> {e}', exc_info=True)
            library = []
            playback = []
    except Exception as e:
        logger.warning(f'failed to load user, error -> {e}', exc_info=True)

    lib = []
    if library:
        for item in library:
            if not item.watchlisted:
                continue
            id, rated, watchlisted, updated = item.media_id, item.rated, item.watchlisted, item.entry_updated
            media = { 
                'media_id': id,
                'rated': rated,
                'watchlisted': watchlisted,
                'entry_updated': updated
            }
            lib.append(media)

    videos = []
    if playback:
        for video in playback:
            videos.append({'video_id': video.video_id, 'watched': video.watched, 'paused_at': video.paused_at, 'duration': video.video_duration, 'entry_updated': video.entry_updated})

    return jsonify({'library': lib, 'videos': videos})


@app.route('/content/v1/d', methods=['POST'])
@token_required
@admin_required
def post_delete_item_id():
    key = session.get('key')
    data = request.get_json()

    if not key or not isinstance(key, str):
        logger.warning(f'endpoint "/content/v1/d" session KEY not found. ({key})')
        return jsonify({'error': 'session KEY not found.'}), 400    

    if not data:
        logger.warning(f'endpoint "/content/v1/d" recieved invalid data. ({data})')
        return jsonify({'error': 'missing JSON data'}), 400
    
    media_id = data.get('media_id')
    if not isinstance(media_id, int):
        logger.warning(f'endpoint "/content/v1/d" recieved invalid data. ({data})')
        return jsonify({'error': 'invalid data.'}), 400



    try:
        DB.delete_media_item(media_id)
    except Exception as e:
        logger.error(f'exception while trying to delete item. (item Id: {media_id}) error -> {e}')
        return jsonify({'error': 'internal error.'}), 400
    
    return jsonify({"message": "item deleted."}), 200


@app.route('/content/v1/r', methods=['POST'])
@token_required
@admin_required
def post_request_data():
    key = session.get('key')
    data = request.get_json()

    if not key or not isinstance(key, str):
        logger.warning(f'endpoint "/content/v1/r" session KEY not found. ({key})')
        return jsonify({'error': 'session KEY not found.'}), 400    
    
    if not data and not isinstance(data, dict):
        logger.warning(f'endpoint "/content/v1/r" recieved invalid data. ({data})')
        return jsonify({'error': 'invalid or missing JSON data'}), 400
    
    if not isinstance(data.get('media_id'), int):
        logger.warning(f'endpoint "/content/v1/r" recieved invalid id. ({data})')
        return jsonify({'error': 'invalid id.'}), 400

    if data.get('category') and data.get('category') not in ['tv', 'movie']:
        logger.warning(f'endpoint "/content/v1/r" recieved invalid category. ({data})')
        return jsonify({'error': 'invalid category.'}), 400



    media_id = data.get('media_id')
    category = data.get('category')
    title = data.get('title')
    year = data.get('year')

    job_id = str(uuid4())
    jobs[job_id] = {'status': 'pending'}


    logger.info(f'User attempting to fetch additional data from TMDB for item (ID: {media_id})... new request data: {data}')
    def fetch_tmdb_job():
        try:
            tmdb_data = TMDBClient().request_tmdb_data(title=title, category=category, year=year)
            if tmdb_data:
                update_id(media_id, tmdb_data)
            jobs[job_id]['status'] = 'done'
        except Exception as e:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = str(e)
            logger.error(f'failed to request / update -> {e}', exc_info=True)


    threading.Thread(target=fetch_tmdb_job).start()

    return jsonify({'job_id': job_id, 'status': 'started'}), 202




# API SERVE VIDEO Endpoints
# API SERVE VIDEO Endpoints
# API SERVE VIDEO Endpoints

@app.route('/play')
@login_required
def serve_video():
    v = request.args.get('v', '')

    if not v:
        return jsonify({'error': 'invalid query.'}), 400

    if v.startswith(".."):
        return jsonify({'error': 'invalid data.'}), 400
    
    if not isinstance(v, str):
        return jsonify({'error': 'invalid data.'}), 400
    


    try:
        video = DB.fetch_video_by_hash(v)
        path = os.path.normpath(video.file_path)
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
    except Exception as e:
        logger.error(f'failed to serve video {v}, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400
    

    return send_from_directory(directory, filename)


@app.route('/subs')
@login_required
def serve_subtitles():
    s = request.args.get('s', '')

    if not s:
        return jsonify({'error': 'invalid query.'}), 400
    
    if s.startswith(".."):
        return jsonify({'error': 'invalid data.'}), 400
    
    if not isinstance(s, str):
        return jsonify({'error': 'invalid data.'}), 400
    


    try:
        subtitles = DB.fetch_subtitle_by_hash(s)
        path = os.path.normpath(subtitles.file_path)
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
    except Exception as e:
        logger.error(f'failed to serve subtitles {s}, exception {e}.', exc_info=True)
        return jsonify({'error': 'internal error.'}), 400


    return send_from_directory(directory, filename)
    

























if __name__ == "__main__":
    create_localdb()
    create_settings()

    sync_thread = threading.Thread(target=sync_libraries)
    sync_thread.start()

    logger.info(f'[ APP ] running... at localhost:8000, 127.0.0.1:8000, {socket.gethostbyname(socket.gethostname())}:8000')
    print(f'\n[ APP ] running... at localhost:8000, 127.0.0.1:8000, {socket.gethostbyname(socket.gethostname())}:8000')
    serve(
        app, 
        ident=None, 
        host="0.0.0.0", 
        port=8000,
        url_scheme='https', 
        threads=8,
        connection_limit=100,
        asyncore_use_poll=True,
        channel_timeout=120,
    )


    # print('\n[ APP ] application is running...')
    # app.run(host="0.0.0.0", port=8000, debug=True)
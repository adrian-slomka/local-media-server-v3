
import os
import time
import json
import requests
import logging
logger = logging.getLogger(__name__)



from dotenv import load_dotenv
load_dotenv()




class TMDBClient:
    BASE_URL = 'https://api.themoviedb.org/3'
    HEADERS = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('API_KEY')}"
    }

    
    def _request(self, endpoint: str, params: dict = None) -> dict:
        """method to make GET requests to the TMDB API."""
        time.sleep(1)  # rate-limit

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.get(url, headers=self.HEADERS, params=params)
            response.raise_for_status() # raises a requests.exceptions.HTTPError.
            logger.debug(f'response status: {response.status_code}')
            return response.json()
        except requests.RequestException as e:
            logger.error(f"request failed: {e} | URL: {url} | Params: {params}", exc_info=True)
            return {} 


    def search(self, title: str, category: str, year: str = None) -> list[dict]:
        """
        Search for a movie or TV show by title.
        """

        params = {
            "query": title,
            "adult": False,
            "language": "en-US",
            "page": 1
        }
        if year:
            params["year" if category == "movie" else "first_air_date_year"] = year

        data = self._request(f"/search/{category}", params)
        return data.get("results", [])


    def get_details(self, category: str, item_id: int) -> dict:
        """
        Get general details for a movie or TV show by ID.
        """

        return self._request(f"/{category}/{item_id}")


    def get_images(self, category: str, item_id: int) -> dict:
        """
        Get images for a movie or TV show by ID.
        """

        return self._request(f"/{category}/{item_id}/images")
    

    def get_videos(self, category: str, item_id: int) -> dict:
        """
        Get trailers etc for a movie or TV show by ID.
        """

        return self._request(f"/{category}/{item_id}/videos")


    def get_release_dates(self, item_id: int) -> dict:
        """
        Get the release dates and certifications for a movie.
        """

        return self._request(f"/movie/{item_id}/release_dates")


    def get_content_ratings(self, item_id: int) -> dict:
        """
        Get content ratings for a movie or TV show by ID.
        """

        return self._request(f"/tv/{item_id}/content_ratings")


    def get_recommendations(self, category: str, item_id: int) -> dict:
        """
        Get recommendations for a movie or TV show by ID.
        """

        return self._request(f"/{category}/{item_id}/recommendations")


    def get_credits(self, category: str, item_id: int) -> dict:
        """
        Get cast & crew for a movie or TV show by ID.
        
        For TV credits this method returns the latest season credit data.
        """

        return self._request(f"/{category}/{item_id}/credits")
    

    def get_aggregate_credits(self, item_id: int) -> dict:
        """
        Get entire cast & crew for all episodes belonging to a TV show.
        """

        return self._request(f"/tv/{item_id}/aggregate_credits")


    def get_tv_seasons(self, item_id: int, season_id: int) -> dict:
        """
        Get details for series' season.
        """

        return self._request(f"/tv/{item_id}/season/{season_id}")

    @staticmethod
    def download_image(url: str, image_type:str):
        """
        Params:
            url (example: /tg9I5pOY4M9CKj8U0cxVBTsm5eh.jpg):
            image_type ('poster' | 'backdrop' | 'logo' | 'still' | 'cast'):
        """
        if not url:
            return
        
        if not isinstance(url, str):
            logger.warning(f'failed to download image ({image_type}): url is not a string.')
            return


        if image_type in ['poster', 'backdrop', 'logo', 'still', 'network', 'production_companie', 'season_poster', 'actor']:
            SAVE_FOLDER = f'static/images/{image_type}s'
        else:
            logger.warning('incorrect image type.', image_type)
            return

        TMDB_SIZES = [         
        "https://image.tmdb.org/t/p/original",  # Original size, px not specified
        ]   

        os.makedirs(SAVE_FOLDER, exist_ok=True)
        for image_size in TMDB_SIZES:
            url_path = image_size+url 
            filename = os.path.join(SAVE_FOLDER, f"{os.path.basename(url)}")
            if os.path.exists(filename):
                continue
            
            time.sleep(1) # rate limit
            try:
                response = requests.get(url_path, stream=True) 
                response.raise_for_status()
            except Exception as e:
                logger.error(f"failed to fetch URL: {url_path}. Status: {e.response.status_code}", exc_info=True)

            if response.status_code == 200:
                with open(filename, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
            else:
                logger.warning(f"failed to download image '{url}' — status code: {response.status_code}")

    def download_all_images(self, data):

        self.download_image(data.get('backdrop_path'), 'backdrop') # Download TV/Movie Backdrop Image
        self.download_image(data.get('poster_path'), 'poster') # Download TV/Movie Poster

        for logo in data.get('logos', []): # Download TV/Movie Title Logo
            self.download_image(logo.get('file_path'), 'logo')



        from library_manager import load_settings # >:-|
        SETTINGS = load_settings()
        if SETTINGS.get('download_extra_images'):

            for network in data.get('networks', []): # Download Network Logo
                self.download_image(network.get('logo_path'), 'network')

            for season in data.get('seasons', []): # Download Season Posters
                self.download_image(season.get('poster_path'), 'season_poster')

            for prod_comp in data.get('production_companies', []): # Download Production Company Logo
                self.download_image(prod_comp.get('logo_path'), 'production_companie')

            # Download Stills for Episodes 
            total_episodes = sum(len(season.get('episodes', [])) for season in data.get('seasons', []))
            logger.debug(f'downloading episodes still frame... ({total_episodes})')

            for season in data.get('seasons', []):
                for episode in season.get('episodes', []):
                    self.download_image(episode.get('still_path'), 'still')
            
            # Download Actor profile pics
            actors_total = len(data.get('cast'))
            logger.debug(f'downloading cast profile images... ({actors_total})')

            for actor in data.get('cast'):
                self.download_image(actor.get('profile_path'), 'actor')

    @staticmethod
    def normalize_logos(images):
        logos = []
        for logo in images.get('logos'):
            if logo.get('iso_639_1') in [logo.get('iso_639_1') for logo in logos]: # after append check for duplciates and skip
                continue
            if not logo.get('iso_639_1') in ['en']: # skip logos that arent in english
                continue
            logos.append(logo) 
        return logos   

    @staticmethod
    def normalize_cast(cast):
        return [
            {
                'adult': actor.get('adult'),
                'gender': actor.get('gender'),
                'id': actor.get('id'),
                'known_for_department': actor.get('known_for_department'),
                'name': actor.get('name'),
                'original_name': actor.get('original_name'),
                'popularity': actor.get('popularity'),
                'profile_path': actor.get('profile_path'),
                'character': actor.get('character'),
                'order': actor.get('order')
            }
            for actor in cast
        ]

    @staticmethod
    def normalize_aggregate_cast(cast):
        return [
            {
                'adult': actor.get('adult'),
                'gender': actor.get('gender'),
                'id': actor.get('id'),
                'known_for_department': actor.get('known_for_department'),
                'name': actor.get('name'),
                'original_name': actor.get('original_name'),
                'popularity': actor.get('popularity'),
                'profile_path': actor.get('profile_path'),
                'character': role.get('character'),
                'episode_count': role.get('episode_count'),
                'total_episode_count': actor.get('total_episode_count'),
                'order': actor.get('order')
            }
            for actor in cast
            for role in actor.get('roles', [])
        ]

    @staticmethod
    def normalize_episodes(season):
        return [
            {
                'air_date': ep.get('air_date'),
                'episode_number': ep.get('episode_number'),
                'episode_type': ep.get('episode_type'),
                'id': ep.get('id'),
                'name': ep.get('name'),
                'overview': ep.get('overview'),
                'runtime': ep.get('runtime'),
                'season_number': ep.get('season_number'),
                'tmdb_id': ep.get('show_id'),
                'still_path': ep.get('still_path'),
                'vote_average': ep.get('vote_average'),
                'vote_count': ep.get('vote_count'),
                'guest_stars': [crew.get('id') for crew in ep.get('crew', [])],
            }
            for ep in season.get('episodes', [])
        ]


    def normalize_seasons(self, tmdb_id, seasons):
        normalized = []
        for tv_season in seasons:
            season_data = self.get_tv_seasons(tmdb_id, tv_season.get('season_number')) # api request
            normalized.append({
                'air_date': season_data.get('air_date'),
                'name': season_data.get('name'),
                'id': season_data.get('id'),
                'poster_path': season_data.get('poster_path'),
                'season_number': season_data.get('season_number'),
                'vote_average': season_data.get('vote_average'),
                'episodes': self.normalize_episodes(season_data),
            })
        return normalized

    @staticmethod
    def normalize_genres(genres: list):
        genre_map = {
            "Science Fiction": "Sci-Fi",
            "Sci-Fi & Fantasy": ["Sci-Fi", "Fantasy"],
            "Action & Adventure": ["Action", "Adventure"],
            "War & Politics": ["War", "Politics"],
            "Mystery & Thriller": ["Mystery", "Thriller"],
        }

        norm_genres = []
        existing_ids = set()
        for genre in genres:
            name = genre.strip()
            if name in genre_map:
                mapped = genre_map[name]
                if isinstance(mapped, list):  # If it needs to be split into multiple
                    for new_name in mapped:
                        if new_name not in existing_ids:
                            norm_genres.append(new_name)
                            existing_ids.add(new_name)
                else:
                    if mapped not in existing_ids:
                        norm_genres.append(mapped)
                        existing_ids.add(mapped)
            else:
                if name not in existing_ids:
                    norm_genres.append(genre)
                    existing_ids.add(name)

        return norm_genres

    @staticmethod
    def normalize_certs(certs: list):
        norm_certs = []
        for cert in certs:
            if cert.get('rating'):
                if not cert.get('rating'):
                    continue
                c = {
                    'rating': cert.get('rating'),
                    'iso_3166_1': cert.get('iso_3166_1')
                }
                if c in norm_certs:
                    continue
                norm_certs.append(c)
            else:
                movie_certs = cert.get('release_dates')
                for movie_cert in movie_certs:
                    if not movie_cert.get('certification'):
                        continue
                    c = {
                        'rating': movie_cert.get('certification'),
                        'iso_3166_1': cert.get('iso_3166_1')
                    }
                    if c in norm_certs:
                        continue
                    norm_certs.append(c)
        return norm_certs


    def build_media_data(self, title: str, tmdb_id: int, category: str, details: dict, images: dict, videos: dict, content_ratings: dict, recommendations: dict, cast_norm: dict, seasons_norm: dict):

        data = {
            'title': title,
            'tmdb_id': tmdb_id,
            'media_type': category,
            'backdrop_path': details.get('backdrop_path'),
            'genres': self.normalize_genres([g.get('name') for g in details.get('genres', [])]),
            'homepage': details.get('homepage'),
            'logos': self.normalize_logos(images),
            'origin_country': details.get('origin_country', []),
            'original_language': details.get('original_language'),
            'original_title': details.get('original_name') or details.get('original_title'),
            'overview': details.get('overview'),
            'popularity': details.get('popularity'),
            'poster_path': details.get('poster_path'),
            'production_companies': details.get('production_companies', []),
            'production_countries': details.get('production_countries', []),
            'spoken_languages': details.get('spoken_languages', []),
            'status': details.get('status'),
            'tagline': details.get('tagline'),
            'vote_average': details.get('vote_average'),
            'vote_count': details.get('vote_count'),
            'content_ratings': self.normalize_certs(content_ratings.get('results', [])),
            'recommendations': [r.get('id') for r in recommendations.get('results', [])],
            'cast': cast_norm,
            'videos': videos.get('results', [])
        }

        if category == 'tv':
            data.update({
                'release_date': details.get('first_air_date'),
                'first_air_date': details.get('first_air_date'),
                'last_air_date': details.get('last_air_date'),
                'networks': details.get('networks', []),
                'number_of_episodes': details.get('number_of_episodes'),
                'number_of_seasons': details.get('number_of_seasons'),
                'seasons': seasons_norm,
            })

        if category == 'movie':
            data.update({
                'budget': details.get('budget'),
                'release_date': details.get('release_date'),
                'revenue': details.get('revenue'),
                'runtime': details.get('runtime'),
            })

        return data


    def request_tmdb_data(self, title, category, year=None):
        """
        Request complete data for given title such as general details, images, content ratings and recommendations and build data dict.
        """
        logger.info(f'Querying for additional details via TMDB API for: "{category}", "{title}", "{year}"...')

        results = self.search(title, category, year)
        if not results:
            logger.warning(f'no results found for: "{title}".')
            return

        titlekey = 'original_title' if category == 'movie' else 'original_name'
        titles = ' | '.join([f'"{item.get(titlekey)}" ({item.get("id")})' for item in results])
        logger.info(f'Found {len(results)} results: {titles}')


        tmdb_id = results[0]['id'] 
        details = self.get_details(category, tmdb_id)
        images = self.get_images(category, tmdb_id)
        videos = self.get_videos(category, tmdb_id)
        recommendations = self.get_recommendations(category, tmdb_id)

        
        cast_norm = []
        seasons_norm = []
        if category == 'movie':
            content_ratings = self.get_release_dates(tmdb_id)
            credits = self.get_credits(category, tmdb_id)
            cast_norm = self.normalize_cast(credits.get('cast', []))
        elif category == 'tv':
            content_ratings = self.get_content_ratings(tmdb_id)
            credits = self.get_aggregate_credits(tmdb_id)
            cast_norm = self.normalize_aggregate_cast(credits.get('cast', []))
            seasons_norm = self.normalize_seasons(tmdb_id, details.get('seasons', []))
        
        try:
            data = self.build_media_data(title, tmdb_id, category, details, images, videos, content_ratings, recommendations, cast_norm, seasons_norm)
        except Exception as e:
            logger.error(f'failed to build a dictionary for {title}', exc_info=True)
            return {}
        


        logger.info(f'Downloading images for: "{category}", "{title}", "{year}"...')
        download_start_time = time.time()

        try:
            self.download_all_images(data)
        except Exception as e:
            logger.error(f'exception {e}, while downloading images for "{title}" ({data.get("tmdb_id")})', exc_info=True)

        logger.info(f'Images downloaded for: "{category}", "{title}", "{year}". ({time.time() - download_start_time:.2f}s)')


        logger.info(f'Completed TMDB API query for: "{category}", "{title}", "{year}".')
        return data


if __name__ == "__main__":
    data = TMDBClient().request_tmdb_data(title='Andor', category='tv')
    print(data)
    

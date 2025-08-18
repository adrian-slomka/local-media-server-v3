import os
import re
import time
import json
import shutil
import threading
import hashlib
import subprocess
import unicodedata
import secrets
import logging
logger = logging.getLogger(__name__)


from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()


from database_utils import DB, insert_new, update_id, insert_video_file, delete_metadata_videos, insert_subtitles
from tmdb_client import TMDBClient



FFMPEG_PATH = os.path.join(os.getcwd(), 'ffmpeg.exe') # used in transcode_to_mp4_264_aac()
FFPROBE_PATH = os.path.join(os.getcwd(), 'ffprobe.exe') # used in get_video_metadata()
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm") # used in is_video_file()
FFMPEG_STILLS_SAVE_DIR = 'static/images/stills/'
HASH_KEY = (os.getenv('FILE_HASH_KEY') or 'd3f4ulT-CHANGE-THIS!!BACKUP_IF_NO_.EVN').encode('utf-8')
AUTH_SIZE = 16

if not os.getenv('FILE_HASH_KEY'):
    logger.warning(
        "Environment variable FILE_HASH_KEY is not set. Using default hash key! "
        "This is insecure and should be changed."
    )



def create_settings():
    if os.path.exists('settings.json'):
        return
    
    template = {
        'libraries': {'movies': [],'tv': []},
        'tmdb_additional_data_requests': True,
        'scheduled_db_updates': True,
        'download_extra_images': True
    }

    try:
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=4)
        logger.info('settings.json created successfully.')
    except Exception as e:
        logger.critical('Failed to create settings.json', exc_info=True)
        raise RuntimeError('Could not create settings.json') from e


def load_settings():
    if not os.path.exists('settings.json'):
        logger.error('setting.json not found.')
        raise FileNotFoundError('settings.json not found.')
        
    try:
        with open('settings.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)       
    except Exception as e:
        logger.critical('Failed to load settings.json', exc_info=True)
        raise RuntimeError('settings.json could not be loaded') from e
    
    if not settings:
        logger.critical('Invalid or missing settings.json')
        raise ValueError('Invalid or missing settings.json')
    return settings


def move_videos_to_own_folders(library_path):
    """
    moves in main lib dir, each standalone video file into its own folder named after the file.
    """
    for filename in os.listdir(library_path):
        if filename.endswith((".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm")):
            file_path = os.path.join(library_path, filename)
            folder_name = os.path.splitext(filename)[0]
            new_folder_path = os.path.join(library_path, folder_name)

            # Create the folder if it doesn't exist
            os.makedirs(new_folder_path, exist_ok=True)

            # Move the file into the new folder
            shutil.move(file_path, os.path.join(new_folder_path, filename))


def create_tv_catalog(library_path: str) -> dict[str, dict]:
    catalog = dict()

    for dirname in os.listdir(library_path):
        full_path = os.path.join(library_path, dirname)
        if not os.path.isdir(full_path):
            continue

        tv_data = {
            'title': extract_title(dirname),
            'hash_key': hash_str(full_path),
            'release_date': extract_year(dirname),
            'media_type': 'tv',
            'library_path': library_path,
            'dirpath': full_path,
            'seasons': []
        }
        

        # Detect subfolders / possibly seasons
        subdirs = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
        seasons_detected = False

        for subdir in subdirs:
            season_number = extract_season_number(subdir)
            if season_number is None:
                continue

            season_path = os.path.join(full_path, subdir)
            episodes = []
            for root, dir, files in os.walk(season_path):
                for fname in files:
                    if not is_video_file(fname):
                        continue

                    episode_metadata = {
                        'file_path': os.path.join(root, fname),
                        'hash_key': hash_str(os.path.join(root, fname)),
                        'episode_number': extract_episode_number(fname),
                        'season_number': season_number
                    }
                    episodes.append(episode_metadata)

            if episodes:
                seasons_detected = True
                tv_data['seasons'].append({
                    'season_number': season_number,
                    'season_name': subdir,
                    'dirpath': season_path,
                    'episodes': episodes
                })

        # If no season folders detected, get all video files in main folder
        if not seasons_detected:
            episodes = []
            for root, dir, files in os.walk(full_path):
                for fname in files:
                    if not is_video_file(fname):
                        continue

                    episode_metadata = {
                        'file_path': os.path.join(root, fname),
                        'hash_key': hash_str(os.path.join(root, fname)),
                        'episode_number': extract_episode_number(fname),
                        'season_number': 1
                    }
                    episodes.append(episode_metadata)

            if episodes:
                tv_data['seasons'].append({
                    'season_number': 1,
                    'season_name': 'Season 1',
                    'dirpath': full_path,
                    'episodes': episodes
                })
        
        # get backup year / try to extract from vidoefile name
        if tv_data.get('year') is None:
            seasons: list = tv_data.get('seasons', [])
            for season in seasons:
                for episode in season.get('episodes', []):
                    episode_file_path: str = os.path.basename(episode.get('file_path'))
                    year = extract_year(episode_file_path)
                    if year:
                        tv_data['year'] = year
                        break

        catalog[dirname] = tv_data

    return catalog


def create_movie_catalog(library_path: str) -> dict[str, dict]:
    catalog = dict()

    for dirname in os.listdir(library_path):
        full_path = os.path.join(library_path, dirname)
        if not os.path.isdir(full_path):
            continue

        movie_data = {
            'title': extract_title(dirname),
            'hash_key': hash_str(full_path),
            'release_date': extract_year(dirname),
            'media_type': 'movie',
            'library_path': library_path,
            'dirpath': full_path,
            'videos': []
        }
        
        for root, dir, files in os.walk(full_path):
            for fname in files:
                if not is_video_file(fname):
                    continue

                video_metadata = {
                    'filename': fname,
                    'file_path': os.path.join(root, fname),
                    'hash_key': hash_str(os.path.join(root, fname))
                }
                movie_data['videos'].append(video_metadata)

        
        # get backup year / try to extract from vidoefile name
        if movie_data.get('year') is None:
            videos: list = movie_data.get('videos', [])
            for video in videos:
                video_file_path: str = os.path.basename(video.get('file_path'))
                year = extract_year(video_file_path)
                if year:
                    movie_data['year'] = year
                    break

        catalog[dirname] = movie_data

    return catalog


def is_video_file(filename):
    return filename.lower().endswith(VIDEO_EXTENSIONS)


def extract_year(filename):
    # Regex pattern for a year between 1900 and 2099
    if not filename:
        return None
    
    pattern = r'(19\d{2}|20\d{2})'
    
    match = re.search(pattern, filename)
    if match:
        return int(match.group(0))
    return None


def extract_season_number(folder_name):
    match = re.search(r'season[\s_]?(\d+)|s[\s_]?(\d+)', folder_name, re.IGNORECASE)
    if match:
        return int(match.group(1) or match.group(2))
    return None


def extract_episode_number(filename):
    patterns = [
        r'^(?P<episode_number>\d{1,3})\.',  # Leading "001." or "01." or "1."
        r'[Ss]\d+[Ee](?P<episode_number>\d+)',  # S01E02 or s01e02
        r'[Ss]eason[\s._-]*\d+[\s._-]*Ep(?:isode)?[\s._-]*(?P<episode_number>\d+)',  # Season 1 Episode 2
        r'[Ee]p(?:isode)?[\s._-]?(?P<episode_number>\d+)',  # Ep05, Episode-03
    ]

    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            episode_str = match.group('episode_number')
            if episode_str.isdigit():
                return int(episode_str)

    return None


def extract_title(title: str):
    # title str example: Example.Media.2024.1080p.WEBRip.1400MB.DD5.1.x264-GalaxyRG
    cleaned_title = re.sub(r'https?://\S+|www\.\S+', ' ', title, flags=re.IGNORECASE)

    pattern = r'^(?P<title>.+?)\.*(\b\d{4}\b|\d{3,4}p)'
    cleaned_title = title.replace("(", "").replace(")", "").replace(".", " ").replace('_', ' ')

    # Junk tokens to strip
    junk_tokens = [
        r'WEB[- ]?Rip', r'BluRay', r'HDTV', r'DVDRip', r'CAM', r'HDRip',
        r'x264', r'x265', r'XviD', r'HEVC',
        r'\bDD5\.1\b', r'AAC', r'MP3', r'FLAC',
        r'\b\w{2,}-RG\b',   # e.g. GalaxyRG, YTS, RARBG
        r'\b\d{3,4}MB\b',   # e.g. 700MB, 1400MB
    ]

    # Remove junk tokens
    for token in junk_tokens:
        cleaned_title = re.sub(token, " ", cleaned_title, flags=re.IGNORECASE)

    # Collapse multiple spaces into one
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()  # Replaces multiple spaces with a single space
    cleaned_title = re.match(pattern, cleaned_title)
    if cleaned_title:
        return cleaned_title.group('title').strip()
    return title


def hash_str(str: str):
    h = hashlib.blake2b(key=HASH_KEY, digest_size=AUTH_SIZE)
    h.update(str.encode('utf-8'))
    return h.hexdigest()


def check_video_encoding(video_path):
        try:
            results = get_video_metadata(video_path)
        except Exception:
            logger.error(f'error while validating video encoding. video: {os.path.basename(video_path)}', exc_info=True)
            return True # Return True to append to compatible since could not retrieve video metadata
        
        if not results:
            return True # Return True to append to compatible since could not retrieve video metadata

        video_codec = results.get('video_codec')
        audio_codec = results.get('audio_codec')
        extension = os.path.splitext(video_path)[1].replace(".","")

        if (video_codec == 'h264' and audio_codec == 'aac' and extension == 'mp4'):
            return True
        return False


def get_video_metadata(video_path): 
    
    # Check if ffprobe binary exists
    if not os.path.exists(FFPROBE_PATH):
        logger.error('ffprobe binary not found.')
        return 
    
    cmd = [
        FFPROBE_PATH,
        '-v', 'error', 
        '-show_entries', 'format=duration,bit_rate', 
        '-show_entries', 'stream=codec_name,width,height,avg_frame_rate,codec_type', 
        '-of', 'json', 
        video_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    metadata = json.loads(result.stdout.decode('utf-8'))
    
    # Extract general metadata
    duration = metadata.get('format', {}).get('duration', None)
    bitrate = metadata.get('format', {}).get('bit_rate', None)
    
    # Extract video stream metadata
    video_stream = next((stream for stream in metadata.get('streams', []) if stream['codec_type'] == 'video'), None)
    width = video_stream.get('width', None) if video_stream else None
    height = video_stream.get('height', None) if video_stream else None
    frame_rate = video_stream.get('avg_frame_rate', None) if video_stream else None
    codec_video = video_stream.get('codec_name', None) if video_stream else None
    
    # Extract audio stream metadata
    audio_stream = next((stream for stream in metadata.get('streams', []) if stream['codec_type'] == 'audio'), None)
    codec_audio = audio_stream.get('codec_name', None) if audio_stream else None
    
    # Calculate Aspect Ratio (Width / Height)
    aspect_ratio = None
    if width and height:
        aspect_ratio = round(width / height, 2)
    
    # If frame rate exists, convert it to float
    frame_rate_float = None
    if frame_rate:
        frame_rate_float = frame_rate_to_float(frame_rate)

    try:
        _duration = int(float(duration))
    except Exception as e:
        logger.debug(f'WARNING could not extract duration ({duration}) -> {e}', exc_info=True)
        _duration = None
    # Return the video metadata in the desired format
    return {
        'resolution': norm_resolution(width, height),
        'duration': _duration,
        'audio_codec': codec_audio,
        'video_codec': codec_video,
        'bitrate': "{:.2f} kbps".format(bitrate_to_kbps(bitrate)),
        'frame_rate': "{:.3f}".format(frame_rate_float) if frame_rate_float else None,
        'width': width,
        'height': height,
        'aspect_ratio': aspect_ratio,
    }


def frame_rate_to_float(frame_rate):
    # Assuming frame_rate is in the form of "num/den" like "25/1"
    try:
        numerator, denominator = map(int, frame_rate.split('/'))
        return numerator / denominator
    except ValueError:
        return float(frame_rate)  # Fallback if it's already a decimal value


def bitrate_to_kbps(bitrate):
    # Assuming bitrate is in bps (bits per second)
    try:
        bitrate = int(bitrate)
        return bitrate / 1000  # Convert to kbps
    except (ValueError, TypeError):
        return 0  # Return 0 if the bitrate is invalid


def convert_duration(duration):
    # Assuming duration is in seconds and converting it to HH:MM:SS format
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'  


def norm_resolution(width: int, height: int):
    if not (width and height):
        return
    # Handle Standard and Cinematic 2.39:1 resolutions
    if 1600 <= height <= 2160:
        return '4K'
    elif 800 <= height <= 1080:
        return '1080p'
    elif 500 <= height <= 720:
        return '720p'
    elif height >= 480:
        return '480p'
    elif height >= 360:
        return '360p'
    elif height >= 240:
        return '240p'
    else:
        return f'{height}p' # Fallback for Unclassified


def remove_file_with_retry(file_path, retries=5, delay=5):
    for attempt in range(retries):
        try:
            os.remove(file_path)
            return
        except PermissionError:
            if attempt < retries - 1:
                logger.warning(f'file is being used, retrying in {delay} seconds...')
                time.sleep(delay)
            else:
                logger.error(f'failed to remove file: {os.path.basename(file_path)}', exc_info=True)                      


def transcode_to_mp4_264_aac(file_path: str):
    """
    Transcodes to x264 aac mp4. Removes old video file afterwards.

    Returns new path string.
    """
    # Check if ffprobe binary exists
    if not os.path.exists(FFMPEG_PATH):
        logger.error('ffmpeg binary not found.')
        return None
    
    output_file = os.path.splitext(file_path)[0] + '.mp4'
    
    # Ensure the output file doesn't already exist
    if os.path.exists(output_file):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        new_file_name = f'{os.path.splitext(file_path)[0]}_{timestamp}.mp4'
        
        logger.warning(
            f'Output file already exists: "{os.path.basename(output_file)}". '
            f'Renaming to "{os.path.basename(new_file_name)}" to avoid overwriting. '
            f'Original base name: "{os.path.basename(file_path)}", Timestamp: {timestamp}'
        )

        output_file = new_file_name
        
    # FFmpeg command to transcode a video using NVIDIA GPU acceleration (NVENC) for video and AAC for audio
    # Subtitles should be extracted separately if needed
    command = [
        FFMPEG_PATH,
        '-i', file_path,
        
        # Video encoding settings
        '-c:v', 'h264_nvenc',       # Use NVIDIA GPU acceleration ("libx264" for CPU encoding)
        '-rc', 'vbr_hq',            # Use high-quality variable bitrate mode
        '-preset', 'fast',          # Encoding speed/quality trade-off: slow > medium > fast
        '-cq:v', '19',              # Constant quality (lower = higher quality)
        '-b:v', '10M',              # Target average video bitrate (e.g. 10 Mbps)
        '-maxrate', '20M',          # Maximum allowed bitrate for complex scenes
        '-bufsize', '40M',          # Bitrate buffer size for rate control
        '-pix_fmt', 'yuv420p',      # Ensures wide compatibility, especially with web players

        # Audio encoding settings
        '-c:a', 'aac',              # Encode audio using AAC
        '-ac', '2',                 # Stereo output (2 audio channels)

        # Output container settings
        '-movflags', '+faststart',  # Move metadata to beginning for faster web playback
        '-f', 'mp4',                # Output format (MP4)
        output_file                 # Output file path
    ]

    try:
        # Using subprocess.Popen to get real-time progress updates from stderr
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

        # Read stderr for progress info
        while True:
            stderr_line = process.stderr.readline()
            if stderr_line == '' and process.poll() is not None:
                break  

            if stderr_line:
                # Check for FFmpeg progress lines, shows: frame, time, fps, bitrate, etc.
                if 'frame=' in stderr_line:
                    try:
                        print(f'{stderr_line.strip()}')
                    except Exception:
                        pass

    except Exception:
        logger.error(f'transcoding file failed: {os.path.basename(file_path)}', exc_info=True)
        return file_path # returns original file path string


    remove_file_with_retry(file_path)
    return output_file


def time_to_seconds(time_str: str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    return hours * 3600 + minutes * 60 + seconds


def ffmpeg_key_frame(video_path, hash_key, duration):
    # Check if ffprobe binary exists
    if not os.path.exists(FFMPEG_PATH):
        logger.error('ffmpeg binary not found.')
        return None
    
    output_name = f'/{hash_key}.jpg'
    output_path = os.path.join(FFMPEG_STILLS_SAVE_DIR, output_name.lstrip('/')) # strip '/' bcuz of path.join quirks, slash needed for db consistency

    if os.path.exists(output_path):
        logger.debug(f'key frame image already exists for hash_key "{hash_key}" at "{output_path}", skipping...')
        return output_name

    # Ensure the folder exists
    os.makedirs(FFMPEG_STILLS_SAVE_DIR, exist_ok=True)

    if not duration:
        return None
    
    duration_seconds = duration
    offset_seconds = duration_seconds * 1/11
    
    # Convert the offset back to HH:MM:SS format
    hours = offset_seconds // 3600
    minutes = (offset_seconds % 3600) // 60
    seconds = int(offset_seconds % 60)
    offset_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    

    cmd = [
        FFMPEG_PATH,
        '-ss', offset_time, 
        '-i', video_path,
        '-frames:v', '1',
        '-vf', "scale='if(gt(a,16/9),-1,1280*1.35)':'if(gt(a,16/9),720*1.35,-1)',crop=1280:720",
        output_path
    ]
    # 'scale=1280:720:force_original_aspect_ratio=increase, crop=iw*0.75:ih*0.75'
    subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding='utf-8', errors='replace'
    )

    if output_name:
        return output_name
    else:
        return None 


def get_subtitles(path: str):
        vtt, srt = find_existing_subtitles(path)
        if vtt:
            vtt = norm_sub_data(vtt)
            return vtt
        if srt:
            vtt = convert_to_vtt(srt)
            vtt = norm_sub_data(vtt)
            return vtt
        
        vtt = extract_subtitles(path)
        if vtt:
            vtt = norm_sub_data(vtt)
            return vtt
        
        logger.debug(f'no subtitles found or extracted for "{os.path.basename(path)}"')
        return []


def find_existing_subtitles(path: str) -> list[dict]:
        filename = os.path.splitext(os.path.basename(path))[0] # filename without .mp4 extension
        dir_path = os.path.dirname(path) # folder where the .mp4 is

        vtt = []
        srt = []
        # go thru all files in the path dir
        for root, folders, files in os.walk(dir_path):
            # check if there are subs in the whole dir that have the same name as video file
            for file in files:
                if file.endswith(".vtt") and os.path.splitext(file)[0] == filename:
                    sub_path = os.path.normpath(os.path.join(root, file))
                    vtt.append({'path': sub_path})

                if file.endswith(".srt") and os.path.splitext(file)[0] == filename:
                    sub_path = os.path.normpath(os.path.join(root, file))
                    srt.append({'path': sub_path})

            # go thru all subfolders in that dir
            for folder in folders:
                # check for any subfolders within that dir that have folder name same as video file and grab all subs from that folder
                if folder == filename:
                    folder_path = os.path.join(root, folder)
                    for file in os.listdir(folder_path):
                        if file.endswith(".vtt"):
                            sub_path = os.path.normpath(os.path.join(folder_path, file))
                            vtt.append({'path': sub_path})

                        if file.endswith(".srt"):
                            sub_path = os.path.normpath(os.path.join(folder_path, file))
                            srt.append({'path': sub_path})

                # check for "subs" folder within dir and grab all the subs from that folder
                if folder == 'subs' or folder == 'Subs':
                    folder_path = os.path.join(root, folder)
                    for file in os.listdir(folder_path):
                        if file.endswith(".vtt"):
                            sub_path = os.path.normpath(os.path.join(folder_path, file))
                            vtt.append({'path': sub_path})
                        if file.endswith(".srt"):
                            sub_path = os.path.normpath(os.path.join(folder_path, file))
                            srt.append({'path': sub_path})
        return vtt, srt                   


def convert_to_vtt(srt: list[dict]) -> list[dict]:
    vtt = []
    for subtitles in srt:
        path = subtitles.get('path')
        new_vtt_path = f'{os.path.splitext(path)[0]}.vtt' # remove extension .srt and add .vtt extensions (dont use .replace)

        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        with open(new_vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for line in lines:
                if re.match(r'\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}', line):
                    line = line.replace(',', '.')
                f.write(line)

        vtt.append({'path': new_vtt_path})

        # # Delete the original SRT file after conversion
        # if os.path.exists(path):
        #     os.remove(path)
    return vtt


def norm_sub_data(subtitles: list[dict]) -> list[dict]:
    ALIAS_MAP = {
        # English
        "eng": "en", "british": "en", "english": "en", "anglais": "en",

        # Spanish
        "spa": "es", "esp": "es", "lat": "es", "latin": "es", "mex": "es",
        "european spanish": "es", "español": "es", "espanol": "es", "spanish": "es", "latin american": "es", "latin america spanish": "es",

        # French
        "fre": "fr", "fra": "fr", "français": "fr", "francais": "fr", "french": "fr", "french canadian": "fr",

        # German
        "ger": "de", "deu": "de", "deutsch": "de", "german": "de",

        # Italian
        "ita": "it", "italiano": "it", "italian": "it",

        # Polish
        "pol": "pl", "polish": "pl", "polski": "pl",

        # Portuguese
        "por": "pt", "ptb": "pt", "bra": "pt", "br": "pt", "brazilian": "pt",
        "brazilian portuguese": "pt", "português": "pt", "portugues": "pt",
        "portuguese": "pt", "portuguese brazilian": "pt",

        # Russian
        "rus": "ru", "рус": "ru", "русский": "ru", "russian": "ru",

        # Japanese
        "jpn": "ja", "jap": "ja", "日本語": "ja", "japanese": "ja",

        # Korean
        "kor": "ko", "한국어": "ko", "korean": "ko",

        # Chinese
        "chi": "zh", "zho": "zh", "zh": "zh", "zhcn": "zh", "zhtw": "zh",
        "中文": "zh", "简体中文": "zh", "繁體中文": "zh", "中文(简体": "zh",
        "中文(繁體": "zh", "普通话": "zh", "mandarin": "zh", "chinese": "zh",
        "廣東話": "zh", "粤语": "zh", "cantonese": "zh",

        # Dutch
        "dut": "nl", "ned": "nl", "nld": "nl", "dutch": "nl", "nederlands": "nl",

        # Czech
        "cze": "cs", "češ": "cs", "czech": "cs", "čeština": "cs",

        # Danish
        "dan": "da", "danish": "da", "dansk": "da",

        # Hungarian
        "hun": "hu", "mag": "hu", "hungarian": "hu", "magyar": "hu",

        # Turkish
        "tur": "tr", "tür": "tr", "turkish": "tr", "türkçe": "tr",

        # Arabic
        "ara": "ar", "arabic": "ar", "العربية": "ar",

        # Hebrew
        "heb": "he", "עברית": "he", "hebrew": "he",

        # Persian/Farsi
        "fas": "fa", "per": "fa", "فارسی": "fa", "farsi": "fa", "persian": "fa",

        # Hindi
        "hin": "hi", "हिन्दी": "hi", "hindi": "hi",

        # Bengali
        "ben": "bn", "বাংলা": "bn", "bengali": "bn",

        # Tamil
        "tam": "ta", "தமிழ்": "ta", "tamil": "ta",

        # Telugu
        "tel": "te", "తెలుగు": "te", "telugu": "te",

        # Thai
        "tha": "th", "ไทย": "th", "thai": "th",

        # Vietnamese
        "vie": "vi", "tiế": "vi", "vnm": "vi", "tiếng việt": "vi", "vietnamese": "vi",

        # Greek
        "gre": "el", "ελλ": "el", "ελληνικά": "el", "greek": "el",

        # Finnish
        "fin": "fi", "suo": "fi", "suomi": "fi", "finnish": "fi",

        # Norwegian
        "nor": "no", "norsk": "no", "norwegian": "no",

        # Romanian
        "rom": "ro", "ron": "ro", "romanian": "ro", "română": "ro", "rum": "ro",

        # Slovak
        "slo": "sk", "slk": "sk", "slovak": "sk", "slovenčina": "sk",

        # Slovenian
        "slv": "sl", "slovenian": "sl", "slovenščina": "sl",

        # Swedish
        "swe": "sv", "sve": "sv", "swedish": "sv", "svenska": "sv",

        # Estonian
        "est": "et", "eesti": "et", "estonian": "et",

        # Lithuanian
        "lit": "lt", "lietuvių": "lt", "lithuanian": "lt",

        # Latvian
        "lav": "lv", "latviešu": "lv", "latvian": "lv",

        # Indonesian
        "ind": "id", "indo": "id", "indonesia": "id", "bahasa indonesia": "id", "indonesian": "id",

        # Malay
        "may": "ms", "malay": "ms", "melayu": "ms", "bahasa melayu": "ms",

        # Ukrainian
        "ukr": "uk", "українська": "uk", "ukrainian": "uk",

        # Bulgarian
        "bul": "bg", "български": "bg", "bulgarian": "bg",

        # Serbian
        "srp": "sr", "српски": "sr", "serbian": "sr",

        # Croatian
        "hrv": "hr", "cro": "hr", "croatian": "hr", "hrvatski": "hr",

        # Bosnian
        "bos": "bs", "bosnian": "bs", "bosanski": "bs",

        # Albanian
        "alb": "sq", "shqip": "sq", "albanian": "sq",

        # Georgian
        "geo": "ka", "ქართული": "ka", "georgian": "ka",

        # Armenian
        "arm": "hy", "հայերեն": "hy", "armenian": "hy",

        # Filipino
        "tgl": "tl", "fil": "tl", "tagalog": "tl", "filipino": "tl",

        # Icelandic
        "ice": "is", "isl": "is", "icelandic": "is", "íslenska": "is",

        # Catalan
        "cat": "ca", "català": "ca", "catalan": "ca",

        # Galician
        "glg": "gl", "galego": "gl", "galician": "gl", "galega": "gl",

        # Basque
        "eus": "eu", "baq": "eu", "basque": "eu", "euskara": "eu",

        # Macedonian
        "mac": "mk", "mkd": "mk", "macedonian": "mk", "македонски": "mk",

        # Kannada
        "kan": "kn", "kannada": "kn",

        # Malayalam
        "mal": "ml", "malayalam": "ml", "മലയാളം": "ml",

        # Norwegian Bokmål
        "nob": "nb", "bokmål": "nb", "bokmal": "nb", "norsk bokmål": "nb",

        # Special Cases
        "traditional": "zh", "sdh": "en", "european": "en", "standard estonian": "et",
        "standard latvian": "lv", "standard malay": "ml", "simplified": "zh",
        "forced": "en", "none": "unknown"
    }

    LANGUAGE_MAP = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pl": "Polish",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "nl": "Dutch",
        "da": "Danish",
        "hu": "Hungarian",
        "cs": "Czech",
        "tr": "Turkish",
        "ar": "Arabic",
        "he": "Hebrew",
        "fa": "Persian",
        "hi": "Hindi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "th": "Thai",
        "vi": "Vietnamese",
        "fi": "Finnish",
        "el": "Greek",
        "no": "Norwegian",
        "ro": "Romanian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "sv": "Swedish",
        "et": "Estonian",
        "lt": "Lithuanian",
        "lv": "Latvian",
        "id": "Indonesian",
        "ms": "Malay",
        "uk": "Ukrainian",
        "bg": "Bulgarian",
        "sr": "Serbian",
        "hr": "Croatian",
        "bs": "Bosnian",
        "sq": "Albanian",
        "ka": "Georgian",
        "hy": "Armenian",
        "tl": "Filipino",
        "is": "Icelandic",
        "ca": "Catalan",
        "gl": "Galician",
        "eu": "Basque",
        "mk": "Macedonian",
        "kn": "Kannada",
        "ml": "Malayalam",
        "nb": "Norwegian Bokmål",
    }
    
    def clean_label(label: str) -> str:
        label = str(label)
        label = unicodedata.normalize('NFKC', label)    # converts "Ｆｒｅｎｃｈ" to "french", normalize unicode characters and convert full-width parentheses to ASCII
        label = label.replace('.', ' ') 
        label = label.replace(',', ' ') 
        label = re.sub(r'\s*\(.*?\)', '', label)    # remove text inside () brackets (including the brackets themselves)
        label = re.sub(r'\s*\[.*?\]', '', label)    # remove text inside [] sq brackets (including the brackets themselves)
        label = re.sub(r'\d+', '', label)           # remove all numbers
        label = label.strip()
        label = label.lower()
        return label if label else 'unknown'
    
    subtitles_norm = []
    for subs in subtitles:
        path = subs.get('path')
        filename = os.path.basename(path)

        patterns = [
            r'_(?P<lang>.*).vtt',
            r'(?P<backup>.*).vtt'
        ]

        label = 'unknown'
        for pattern in patterns:
            match = re.search(pattern, filename)

            if match:
                if 'lang' in match.groupdict():
                    label = match.group('lang')
                elif 'backup' in match.groupdict():
                    label = match.group('backup')
                break
        

        label = clean_label(label)
        if len(label.split()) > 4:
            label = 'en'  # if the string after split is longer than 4, it means that the .vtt is probably a video file name like so "28 Days Later 2002.vtt" which usually means it's default english

        srclang = "unknown"
        # Try direct match in LANGUAGE_MAP (ISO codes)
        if label in LANGUAGE_MAP:
            srclang = label  
        # Try ALIAS_MAP (common name/alias to ISO code)
        elif label in ALIAS_MAP:
            srclang = ALIAS_MAP.get(label, 'unknown')
        # Try split and match first word... example. "Portuguese Brazilian"
        elif label.split()[0] in ALIAS_MAP:
            srclang = ALIAS_MAP.get(label.split()[0], 'unknown')
            

        label_out = LANGUAGE_MAP.get(srclang, 'unknown')
        hash_key = hash_str(path)
        subtitles_norm.append({
            'path': path,
            'lang': srclang,
            'label': label_out,
            'hash_key': hash_key
        })
        if label_out == 'unknown' or srclang == 'unknown':
            logger.debug(f"unknown subtitle language detected. label: '{label}', srclang: '{srclang}', label_out: '{label_out}', filename: '{filename}', key: '{hash_key}'")

    return subtitles_norm


def extract_subtitles(video_path: str) -> list[dict]:
    FFPROBE_PATH = os.path.join(os.getcwd(), 'ffprobe.exe')
    FFMPEG_PATH = os.path.join(os.getcwd(), 'ffmpeg.exe')

    if not os.path.exists(FFPROBE_PATH):
        logger.error(f'ffprobe binary not found.')
        return []
    if not os.path.exists(FFMPEG_PATH):
        logger.error(f'ffmpeg binary not found.')
        return []
    
    # Get subtitle streams info using ffprobe
    probe_cmd = [
        FFPROBE_PATH,
        '-v', 'error',
        '-select_streams', 's', 
        '-show_entries', 'stream=index:stream_tags=title,language', 
        '-of', 'json',
        video_path
    ]
    result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

    # Parse the ffprobe output and extract subtitle streams
    try:
        subtitles = json.loads(result.stdout).get("streams", [])
    except json.JSONDecodeError as e:
        logger.warning(f'error parsing ffprobe output for video: {os.path.basename(video_path)}', exc_info=True)
        return []
    if not subtitles:
        return []
    
    output_folder = f'{os.path.dirname(video_path)}/{os.path.splitext(os.path.basename(video_path))[0]}' 
    output_folder_norm = os.path.normpath(output_folder)
    os.makedirs(output_folder_norm, exist_ok=True)  # Ensure output folder exists

    extracted_subs = []    
    for adjusted_index, subs in enumerate(subtitles):
        index = subs.get('index', 0) # Original Index
        label = subs.get('tags', {}).get('title', 'unknown')
        lang = subs.get('tags', {}).get('language', 'unknown')
        # Create an output directory based on the video file name
        output_path = os.path.join(output_folder_norm, f"{index}_{label}.vtt") if label else os.path.join(output_folder_norm, f"{index}_{lang}.vtt")

        # ffmpeg command to extract the subtitles
        extract_cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            F'-map', f'0:s:{adjusted_index}',     # Map subtitle stream by index
            '-c:s', 'webvtt',           # Convert to VTT format
            '-y',                       # Overwrite if already exists
            output_path
        ]   
        subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        
        if output_path:
            data = {
                'index': index,
                'path': output_path,
                'lang': lang,
                'label': label
            }
            extracted_subs.append(data)
        else:
            logger.debug(f'failed to extract subtitles from video container for {os.path.basename(video_path)}, output path: {os.path.basename(output_path)}', exc_info=True)
    return extracted_subs






def process_libraries(libraries: dict[str, list]) -> dict[str, dict]:
    tv_catalog = dict()
    movies_catalog = dict()

    for lib_name, lib_paths in libraries.items():
        for path in lib_paths:
            norm_path = os.path.normpath(path)
            move_videos_to_own_folders(norm_path)

            if lib_name == 'tv':
                media_catalog = create_tv_catalog(norm_path)
                tv_catalog.update(media_catalog)

            elif lib_name == 'movies':
                media_catalog = create_movie_catalog(norm_path)
                movies_catalog.update(media_catalog)

    catalog = dict()
    catalog['tv'] = tv_catalog
    catalog['movies'] = movies_catalog 

    logger.info(f'TV Shows: {len(tv_catalog)} | Movies: {len(movies_catalog)}')         
    return catalog


def insert_entry(existing_entries: list[str], catalog: dict[str, dict]):
    """
    Insert new main entry tv series or movie to database.

    Params:
        existing_entries (list): a list of hash keys from database
        catalog (dict[str, dict]): a dict with media catalogs { 'tv': tv_catalog, 'movies': movies_catalog }

    Returns:
        an updated list with the new entries of already existing (in database) hash keys
    """
    for media_catalog in catalog.values(): # catalog = { 'tv': tv_catalog, 'movies': movies_catalog }

        for tv_movie_dict in media_catalog.values(): # tv_catalog = { 'tv_show_name': data } / movies_catalog = { 'movie_name': data }
            
            hash_key = tv_movie_dict.get('hash_key')
            if hash_key and hash_key not in existing_entries:
                try:
                    insert_new(tv_movie_dict)
                except Exception:
                    logger.error(f"failed to insert item with title '{tv_movie_dict.get('title', 'Unknown')}' and hash_key '{hash_key}' into database.", exc_info=True)
                    continue


def identify_new_videos(existing_videos: set[str], catalog: dict[str, dict]) -> tuple[set, list[tuple[str, dict]]]:
    """
    Identify videos that are present locally but not yet recorded in the database.

    Args:
        existing_video_hashes (set[str]): Set of hash keys for videos already in the database.
        media_catalog (dict[str, dict]): Dictionary containing 'movies' and 'tv' catalogs, 
            each mapping media items to their data including video hashes.

    Returns:
        tuple: 
            - all_local_video_hashes (set): All video hash keys found in the local catalog.
            - new_videos (list): List of tuples (parent_media_hash_key, video_data) for videos not yet in the database.
    """
    all_local_video_hashes  = set()
    new_videos = []

    for media_type, media_catalog in catalog.items():
        if media_type == 'movies':
            # -- Movies
            for data in media_catalog.values():
                for video_data in data.get('videos', []):
                    hash_key = video_data.get('hash_key')
                    if not hash_key:
                        continue

                    all_local_video_hashes.add(hash_key)
                    if hash_key not in existing_videos:
                        new_videos.append((data.get('hash_key'), video_data))

        elif media_type == 'tv':
            # -- TV Episodes
            for data in media_catalog.values():
                for season in data.get('seasons', []):
                    for episode in season.get('episodes', []):
                        hash_key = episode.get('hash_key')
                        if not hash_key:
                            continue

                        all_local_video_hashes.add(hash_key)
                        if hash_key not in existing_videos:
                            new_videos.append((data.get('hash_key'), episode))
    return all_local_video_hashes, new_videos


def process_and_insert_videos(videos: dict[str, list[tuple[str, dict]]]):
    """
    Process video files by inserting metadata for compatible files and transcoding
    incompatible files before inserting their metadata, including subtitles.

    Args:
        videos (dict): Dictionary with keys 'compatible' and 'incompatible', each
                       containing a list of (item_hash, video_data) tuples.
    """
    
    def extract_and_insert(item_hash, video_data, transcode=False):
        video_path = video_data.get('file_path')
        video_name = os.path.basename(video_path)
        logger.debug(f'processing video: transcode="{transcode}", hash_key="{item_hash}", video="{video_name}"...')

        subtitles = get_subtitles(video_path)  # Extract subtitles before transcoding
        
        if transcode:
            logger.info(f'Starting transcoding video: {video_name}')
            start_time = time.perf_counter()
            
            video_path = transcode_to_mp4_264_aac(video_path)
            video_data['file_path'] = video_path
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.info(f'finished transcoding video: {video_name} (took {duration:.2f} seconds)')
        
        results = get_video_metadata(video_path)
        if not results:
            logger.warning(f'failed to get metadata for video: {video_name}')
            return
        logger.debug(f'video metadata obtained: resolution="{results.get("resolution")}", duration={results.get("duration")}, codecs="{results.get("audio_codec")}/{results.get("video_codec")}"')
        
        extra_metadata = {
            'size': os.path.getsize(video_path),
            'resolution': results.get('resolution'),
            'duration': results.get('duration'),
            'audio_codec': results.get('audio_codec'),
            'video_codec': results.get('video_codec'),
            'bitrate': results.get('bitrate'),
            'frame_rate': results.get('frame_rate'),
            'width': results.get('width'),
            'height': results.get('height'),
            'aspect_ratio': results.get('aspect_ratio'),
            'key_frame': ffmpeg_key_frame(video_path, video_data.get('hash_key'), results.get('duration')),
            'extension': os.path.splitext(video_path)[1].replace(".", "")
        }
        video_data.update(extra_metadata)
        video_data['subtitles'] = subtitles if subtitles else []

        item = DB.fetch_by_hash_key(item_hash)
        if not item:
            logger.warning(f'MediaItem not found in the database with hash_key: "{item_hash}"')
            return
        
        metadata_row_id = insert_video_file(item.id, video_data)
        logger.debug(f'inserted video (ID: {metadata_row_id})')

        if video_data.get('subtitles'):
            insert_subtitles(metadata_row_id, video_data.get('subtitles'))
            logger.debug(f'inserted {len(video_data["subtitles"])} subtitle(s) for video (ID: {metadata_row_id})')
    
    for encoding, videos in videos.items():
        if encoding == 'compatible':
            logger.info("Processing compatible files...")
            for item_hash, video_data in videos:
                extract_and_insert(item_hash, video_data, transcode=False)

        else:
            logger.info("Processing incompatible files... (this process might take a while)")
            for item_hash, video_data in videos:
                extract_and_insert(item_hash, video_data, transcode=True)


def request_and_udpdate_with_additional_data(catalog: dict[str, dict[str, dict]]):
    for media_catalog in catalog.values(): # catalog = { 'tv': tv_catalog, 'movies': movies_catalog }
        
        for tv_movie_dict in media_catalog.values(): # tv_catalog = { 'tv_show_name': data } / movies_catalog = { 'movie_name': data }
    
            key = tv_movie_dict.get('hash_key')

            item = DB.fetch_by_hash_key(key)
            if not item:
                logger.warning(f'item not found in the database with hash_key: "{key}"')
                return
            
            last_updated = item.entry_updated if item.entry_updated else 0 # unix time
            unix_now = int(datetime.now(timezone.utc).timestamp()) # unix time
            day = 86400 # day in seconds
            if unix_now - last_updated < day: # request from TMDB API only if it's been more than a day since last updated, otherwise skip entry
                logger.debug(f"Skipping TMDB request for {item.title} ({item.id}): last updated {round((unix_now - last_updated) / 3600, 0)}h ago (<1 day)")
                continue

            try:
                row_id = item.id    
                title = tv_movie_dict['title']
                category = tv_movie_dict['media_type']
                year = tv_movie_dict.get('release_date')
            
                tmdb_data = TMDBClient().request_tmdb_data(title=title, category=category, year=year)

                if tmdb_data:
                    update_id(row_id, tmdb_data)

            except Exception:
                logger.warning(f'failed to update item id:{row_id} ("{title}") with TMDB data.', exc_info=True) 




def sync_libraries():
    settings = load_settings()
    logger.info(f'Initializing library verification...')
    


    # 1. Process libraries and build catalog for tv shows and movies
    logger.info(f'Scanning library...')

    libraries: dict[str, list] = settings.get('libraries')
    catalog: list[dict] = process_libraries(libraries)



    # 2. Insert new TV shows and movies basic info (title, optional year, hash key) into the database.
    #    Return the updated set of existing hash keys including newly inserted entries.
    logger.info('Inserting new items with basic info for further processing (e.g., fetching additional data from TMDb)...')

    existing_entries: set[str] = set(DB.fetch_hash_MediaItem())
    insert_entry(existing_entries, catalog) 



    # 3. Identify videos that are present locally but not yet recorded in the database.
    #    Return: 1) updated list of already existing videos in database with new videos hashes, 2) a tuple with the hash key and a list of videos data
    logger.info('Identifying new local videos not yet recorded in the database...')

    existing_videos = set(DB.fetch_hash_VideoMetadata())
    all_local_video_hashes, new_videos = identify_new_videos(existing_videos, catalog)



    # 3. Remove video files from the database that are no longer found locally
    missing_hashes = existing_videos - all_local_video_hashes
    logger.info(f'Removing {len(missing_hashes)} video(s) from database that no longer exist locally...')

    if missing_hashes:
        delete_metadata_videos(missing_hashes)



    # 4. Check for html compatibility and transcode
    logger.info(f"Checking HTML compatibility of new videos...")
    compatible_encoding = []
    incompatible_encoding = []
    for item_hash, video_data in new_videos:
        if check_video_encoding(video_data.get('file_path')):
            compatible_encoding.append((item_hash, video_data))
        else:
            incompatible_encoding.append((item_hash, video_data))

    videos = dict()
    videos['compatible'] = compatible_encoding
    videos['incompatible'] = incompatible_encoding
    logger.info(f"Processed {len(new_videos)} new videos: {len(compatible_encoding)} compatible with HTML5, {len(incompatible_encoding)} require transcoding.")



    # 5. Insert videos with compatible encoding to metadata table
    # process_and_insert_videos(videos)
    thread_videos = threading.Thread(target=process_and_insert_videos, args=(videos,))



    # 6. Request data for tv/movie title from tmdb api
    thread_tmdb = None
    if settings.get('tmdb_additional_data_requests'):
        # request_and_udpdate_with_additional_data(catalog)
        thread_tmdb = threading.Thread(target=request_and_udpdate_with_additional_data, args=(catalog,))


    # 7. 
    thread_videos.start()
    if thread_tmdb:
        thread_tmdb.start()

    # Wait for both threads to finish before moving on
    thread_videos.join()
    if thread_tmdb:
        thread_tmdb.join()



    logger.info(f'Library verification completed.')
















if __name__ == "__main__":
    # create_settings()
    sync_libraries()
    




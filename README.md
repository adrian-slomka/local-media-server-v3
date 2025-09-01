# Local Media Server

A Python-based web application made with Flask that serves as a local media server similar to Plex or Jellyfin.

## Preview

![App Screenshot](https://raw.githubusercontent.com/adrian-slomka/local-media-server-v3/refs/heads/main/___preview/Screenshot%202025-08-18%20at%2010-13-22%20Stream%20Movies%20&%20TV%20Shows.png)

![App Screenshot](https://raw.githubusercontent.com/adrian-slomka/local-media-server-v3/refs/heads/main/___preview/Screenshot%202025-08-18%20at%2010-13-11%20Stream%20Movies%20&%20TV%20Shows.png)

![App Screenshot](https://raw.githubusercontent.com/adrian-slomka/local-media-server-v3/refs/heads/main/___preview/Screenshot%202025-08-18%20at%2010-14-04%20Stream%20Movies%20&%20TV%20Shows.png)


## Features

- **Web UI**: Easy to use and responsive web UI with a dynamic search and watchlist features.
- **Multiple Accounts**: Multiple accounts for multiple users to track individual progress and watchlist.
- **Resume Playback Across Devices**: Begin watching a video on your desktop and seamlessly continue from the last watched minute on your mobile device, with your viewing progress saved automatically.
- **Display When's Next Episode Air Date**: Always know when's the next episode of your favorite show coming out.
- **(WIP) Automatic TMDB Updates**: Metadata, posters, cast, and episode details are fetched and kept up to date in the background, so library is always up to date.
- **Lightweight Database**: Data saved into light-weight sqlite3 database for simplicity and easy access.

## Requirements

- **NVIDIA GPU**: for NVENC encoding.
- **Python 3.8+**: [python.org](https://www.python.org/downloads/).
- **FFmpeg**: FFmpeg for re-encoding media files.

**with minor changes to the code, encoding can be changed to CPU instead.

## Installation

1. Clone the repo:

    ```
    git clone https://github.com/adrian-slomka/local-media-server-v3.git
    ```

2. Set up [Virtual environment](https://docs.python.org/3/library/venv.html) (optional):


3. Install required dependencies:

    ```
    pip install -r requirements.txt
    ```


4. Install recent [**NVIDIA drivers**](https://www.nvidia.com/en-us/drivers/).


5. Get **FFmpeg**: From [FFmpeg's official website](https://ffmpeg.org/download.html) download pre-compiled exe (builds from gyan.dev). Extract FFprobe.exe and FFmpeg.exe inside the app's main folder.


6. Create .env file in app's main folder with the following variables

    ```
    API_KEY=YOUR_TMDB_API_KEY
    FLASK_KEY=RandomlyGeneratedKey
    FILE_HASH_KEY=CanBeRandomLettersAndNumbers
    DEFAULT_ADMIN_ACCOUNT=UpToYou_ItsYourLogin
    ```

- To aquire TMDB API KEY go to [TMDB](https://developer.themoviedb.org/docs/getting-started) and follow steps provided there.

- To generate a quick FLASK_KEY, use python's library 'secrets' with secrets.token_hex(16). Copy the output and paste it into FLASK_KEY.

    ```
    python -c "import secrets; print(secrets.token_hex(16))"
    ```




## How To Use

1. Start the app:

    ```
    python app.py
    ```

    or via provided .bat file (check .bat since by default it uses venv path)

2. The web application will be accessible on [http://localhost:8000](http://localhost:8000). Open this URL in your web browser. Additionally, the app can be accessed on mobile devices when connected to the same wi-fi network:
    - Get your hosting PC's local ip4 adress (open cmd and type: ipcofing and look for ipv4). 
    - Next, on your mobile device connected to the same Wi-Fi network type that ip adress followed by :8000, example: 192.168.0.100:8000

3. To add your media files first create folder where you will store your movies or series. An ideal folder structure:
    ```
    library/
    ├── movies/
    │   ├── Movie1.mp4
    │   └── Movie2.mp4
    └── tv/
        ├── Wednesday/
        │   ├── Season 1/      (or S1, S01)
        │   │   ├── Episode1.mp4
        │   │   ├── Episode2.mp4
        │   │   └── ...
        │   └── Season 2/
        │       └── ...
        └── AnotherSeries/
            └── Season 1/
                └── ...
    ```
    - Movies can be placed directly inside the movies/ folder. They will automatically be moved into their own folders.
    - For TV series, create a folder for each series inside tv/, then create season folders (Season 1, S1, or S01) and place episodes (.mp4 files) inside.
    - If a movie or series isn’t fetching proper data from TMDB, you can add the release year to the top folder name, e.g., "Wednesday 2022".

4. In the app's main folder, open settings.json and paste your path/s like so (don't forget commas): 
    ```
    "libraries": {"series": ["D:/library/series", "F:/libraryX/series222"], "movies": ["D:/library/movies"] },
    ``` 

5. The app will always scan for new files on .bat start. Additionally, user with admin permission can re-scan library using button on the home page.

6. If no subtitles are found or extracted from the video container, you can add them manually and then re-scan library. 
    - Single subtitle: Place it in the same folder as the video, with the same name as the video file.
    - Multiple subtitles: Create a folder with the same name as the video or episode and put all subtitle files inside.
    - **Re-scan requirement**: If the video was already scanned and added, you’ll need to temporarily move the video file or its folder out of the library and do a library re-scan. After that, add your subtitles and re-scan again.
    - Language codes: Add a language code suffix (e.g., _en, _eng, _english, _fr) to the subtitle filename. Without it, the subtitle will be displayed as "unknown".

    - Example visualized folder structure:

        ```
        library/
        ├── movies/
        │   ├── MovieTitle1/
        │   │   ├── Movie123.mp4
        │   │   └── Movie123.srt       <-- single subtitle in same folder
        └── tv/
            ├── Wednesday/
            │   ├── Season 1/
            │   │   ├── Episode1.mp4
            │   │   ├── Episode1/       <-- multiple subtitles for this episode
            │   │   │   ├── 1_eng.srt    <-- add the _en / _eng / _english, without it will be displayed as 'unknown'
            │   │   │   ├── 2_english.srt
            │   │   │   ├── Episode1_en.srt
            │   │   │   └── 3_fr.srt
        ```
        *Subtitles with .srt extension will be auto converted to .vtt for html compatibility.*


## Limitations

- **Re-encoding Performance**: Since the app uses GPU acceleration, re-encoding large files or a large number of files may take a while and can put a significant load on your system.
- **Unoptimized for slow connection**: By default, images like posters, backdrops, logos and more are downloaded and displayed at full resolution. 
- !! **Security over internet**: I'm no expert, the app was made strictly for local, home wi-fi use only. If you do choose to port forward and use it over the net be aware that the security may be subpar.


## FAQ

### Will the app run without TMDB API KEY?
Yes. However extended info, poster and backdrops will be missing.

### Can I run this app on a non-NVIDIA machine?
Yes. However it requries a small code change. Look for function called "transcode_to_mp4_264_aac()" and you can change nvenc to whatever you prefer there.

### Will the app run without FFmpeg?
No. This is needed for some critical processes.

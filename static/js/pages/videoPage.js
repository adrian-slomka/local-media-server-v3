import { apiFetch } from '../api/_api.js';
import { jsTheme } from '../player/videoPlayerTheme.js';
import { trackTime, setTime } from '../player/videoTimeTracker.js';
import { captionPreference } from '../player/captionPreferences.js';

class VideoElement {
    constructor(containerSelector) {
        this.parentElement = document.getElementById(containerSelector);
        if (!this.parentElement) {
            throw new Error('Container not found: ' + containerSelector);
        }
        this.player = null;
        this.videoElement = null;
    }

    insertVideo({ videoSrc, previewImg, videoId, itemId, startTime = 0, duration = 0 }) {
        const video = document.createElement('video');
        video.id = 'video';
        video.className = 'video-canvas vjs-crunchy-theme';
        video.setAttribute('controls', '');
        video.setAttribute('data-setup', JSON.stringify({
            controls: true,
            autoplay: false,
            preloadTextTracks: false
        }));
        video.setAttribute('video-id', videoId);
        video.setAttribute('item-id', itemId);
        video.setAttribute('start-time-data', startTime);
        video.setAttribute('duration-data', duration);
        if (previewImg) {
            video.setAttribute('poster', `/static/images/stills${previewImg}`);
        }
        

        // Insert source
        const source = document.createElement('source');
        source.src = videoSrc;
        source.type = 'video/mp4';
        video.appendChild(source);

        this.parentElement.appendChild(video);
        this.videoElement = video;
    }

    async insertSubtitles(sub) {
        if (!this.videoElement) {
            throw new Error('video element not found.');
        }
        const track = document.createElement('track');

        track.src = `/subs?s=${sub.hash_key}`;
        track.kind = sub.kind || 'subtitles';
        track.srclang = sub.lang;
        track.label = sub.label;
        track.default = false;

        this.videoElement.appendChild(track)
    }

    initVideoJS() {
        this.player = videojs(this.videoElement.id, {
            userActions: {
                hotkeys: {
                    playPauseKey: function(event) {return (event.which === 32);},
                    fullscreenKey: event => event.which === 86
                }
            },
            // controlBar: {skipButtons: {forward: 5, backward: 10}}, 
            spatialNavigation: {enabled: true, horizontalSeek: true}, 
            html5: {preloadTextTracks: false, nativeControlsForTouch: true}
        });

        document.getElementById('video').classList.add('video-js');
        jsTheme(this.player)
        return this.player;
    }
}


class PageDetails {
    constructor(pageTitle, mediaId, mediaTitle, mediaEpisode, videoReleased, videoOverview) {
        this.pageTitleEl = document.getElementById(pageTitle);
        this.mediaIdEl = document.getElementById(mediaId);
        this.mediaTitleEl = document.getElementById(mediaTitle);
        this.mediaEpisodeEl = document.getElementById(mediaEpisode);
        this.videoReleasedEl = document.getElementById(videoReleased);
        this.videoOverviewEl = document.getElementById(videoOverview);
    }

    async updatePage(item, video, mediaId) {
        const pageT = video?.season_number
            ? `Season ${video.season_number || 0} Episode ${video.episode_number || 0}${video.name ? " - " + video.name : ""}`
            : '';

        if (this.pageTitleEl) {
            this.pageTitleEl.textContent = `Watching: ${item.original_title || item.title || ""} ${pageT}`;
        }

        if (this.mediaIdEl) {
            this.mediaIdEl.href = '/' + mediaId;
        }

        if (this.mediaTitleEl) {
            this.mediaTitleEl.textContent = item.original_title || item.title || "";
        }

        if (this.mediaEpisodeEl) {
            this.mediaEpisodeEl.textContent = video?.season_number
                ? `S${video.season_number || 0} E${video.episode_number || 0}${video.name ? " - " + video.name : ""}`
                : '';
        }

        const date = video?.air_date || item.release_date || "";
        if (this.videoReleasedEl) {
            this.videoReleasedEl.textContent = date ? `Released ${date}` : "";
        }

        if (this.videoOverviewEl) {
            this.videoOverviewEl.textContent = video?.overview || "";
        }
    }
}


class VideoPageLoader {
    constructor(itemId, videoId) {
        this.id = itemId;
        this.videoId = videoId;

        this.video = new VideoElement('v');
        this.page = new PageDetails('page-title', 'mediaId', 'media-title', 'media-ep', 'video-released', 'video-overview');
    }

    async load() {
        const [item, nextVideos, video, account] = await Promise.all([
            apiFetch(`/content/v1/item/${this.id}`).then(res => res.json()),
            apiFetch(`/content/v1/item/${this.id}/videos`).then(res => res.json()),
            apiFetch(`/content/v1/video/${this.videoId}`).then(res => res.json()),
            apiFetch(`/accounts/v1/p?v=${this.videoId}`).then(res => res.json())
        ]);

        // async - Insert Video Source
        this.video.insertVideo({
            videoSrc: `/play?v=${video.hash_key}`,
            previewImg: video.still_path || video.metadata.key_frame,
            videoId: this.videoId,
            itemId: this.id,
            startTime: account.video_start_time,
            duration: video.duration
        });

        // async - Update UI
        this.page.updatePage(item, video, this.id);

        // await all - Insert Subtitles Tracks
        const subs = video.subtitles
        if (Array.isArray(subs) && subs.length > 0) {
            await Promise.all(subs.map(sub => this.video.insertSubtitles(sub)));
        }

        // Init videojs()
        const player = this.video.initVideoJS();

        // load scripts videojs dependant
        captionPreference(player);
        setTime(player, account.video_start_time);
        trackTime(player, this.id, this.videoId);
        return player
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const path = window.location.pathname; // "/12/watch/240"
    const parts = path.split('/');          // ["", "12", "watch", "240"]
    const itemId = parseInt(parts[1], 10);  // MediaItem.id 12
    const videoId = parseInt(parts[3], 10);  // video id 240

    if (isNaN(itemId) || isNaN(videoId)) {
        console.error('Invalid IDs');
        return
    }

    const videoPage = new VideoPageLoader(itemId, videoId);
    const player = await videoPage.load();


    // arrow key seeking for desktop
    document.addEventListener('keydown', function(event) {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
        if (event.which === 37) { // left arrow
            player.currentTime(Math.max(0, player.currentTime() - 5));
            event.preventDefault();
        } else if (event.which === 39) { // right arrow
            player.currentTime(player.currentTime() + 5);
            event.preventDefault();
        }
    }); 
});
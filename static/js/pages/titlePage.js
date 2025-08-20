import { apiFetch } from '../api/_api.js';

class Background {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }
    clear() {
        if (this.container) this.container.innerHTML = '';
    }
    setImage(path) {
        this.clear();
        if (path) {
        const img = document.createElement('img');
        img.src = `static/images/backdrops${path}`;
        img.alt = 'Backdrop Image';
        this.container.appendChild(img);
        } else {
        this.container.textContent = 'No backdrop image available';
        }
    }
}

// Class for logo image with fallback text
class Logo {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }
    clear() {
        if (this.container) this.container.innerHTML = '';
    }
    setLogo(logos, fallbackText) {
        this.clear();
        if (logos && logos.length > 0) {
        const logo = logos.find(l => l.lang === 'en') || logos[0];
        const img = document.createElement('img');
        img.src = `static/images/logos${logo.file_path}`;
        img.alt = fallbackText;

        const fallback = document.createElement('span');
        fallback.className = 'fallback-text';
        fallback.textContent = fallbackText;
        fallback.style.display = 'none';

        img.onerror = () => {
            img.style.display = 'none';
            fallback.style.display = 'block';
        };

        this.container.appendChild(img);
        this.container.appendChild(fallback);
        } else {
        const fallback = document.createElement('span');
        fallback.className = 'fallback-text';
        fallback.textContent = fallbackText;
        fallback.style.display = 'grid'
        this.container.appendChild(fallback);
        }
    }
}

// Class to handle item info
// Media type, Release year, Content rating, Networks
class ItemInfo {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }
    clear() {
        if (this.container) this.container.innerHTML = '';
    }
    createTag(className, id, text) {
        const div = document.createElement('div');
        div.className = className;
        div.id = id;
        div.textContent = text;
        this.container.appendChild(div);
    }
    getYear(dateStr) {
        return dateStr ? dateStr.slice(0, 4) : '';
    }
    load(item, ratings, networks) {
        this.clear();

        // Media type
        this.createTag(
        'media-content-rating -media-padding --round --border',
        'media-type',
        (item.media_type || '').toUpperCase()
        );

        // Release year
        this.createTag(
        'media-release -media-padding --round --border',
        'release-year',
        this.getYear(item.release_date)
        );

        // Content rating
        if (Array.isArray(ratings) && ratings.length > 0) {
            const contentRatingObj = ratings.find(r => r.country === 'GB' || r.country === 'US');
            if (contentRatingObj?.rating) {
            this.createTag(
                'media-content-rating -media-padding --round --border',
                'content-ratings',
                contentRatingObj.rating
            );
            }
        };


        // Networks
        if (Array.isArray(networks) && networks.length > 0) {
        networks.forEach(network => {
            if (network.name?.trim()) {
            this.createTag(
                'media-networks -media-padding --round --border',
                'networks',
                network.name
            );
            }
        });
        }
    }
}


class Genres {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }
    clear() {
        if (this.container) this.container.innerHTML = '';
    }
    createTag(className, id, text) {
        const div = document.createElement('div');
        div.className = className;
        div.id = id;
        div.textContent = text;
        this.container.appendChild(div);
    }
    load(genres) {
        this.clear();
        if (Array.isArray(genres) && genres.length > 0) {
        genres.forEach(genre => {
            if (genre.trim()) {
            this.createTag('media-genre -media-padding --round --border', 'genre', genre);
            }
        });
        }
    }
}

// Class for playback UI
class VideoData {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        if (!this.container) throw new Error(`Container not found: ${containerSelector}`);

        this.episodeInfoElem = this.container.querySelector('[data-t="video-info"]');
        this.durationElem = this.container.querySelector('[data-t="video-duration-info"]');
        this.progressBarElem = this.container.querySelector('[data-t="video-progress-bar"] > .__continue-progress-bar__progress');
        this.statusElem = this.container.querySelector('[data-t="video-status"]');

        this.hasData = false; // Track if any data is set
    }
    setEpisodeInfo(text) {
        if (this.episodeInfoElem && text) {
            this.episodeInfoElem.textContent = text;
            this.hasData = true;
        }
    }
    setDuration(text) {
        if (this.durationElem && text) {
            this.durationElem.textContent = text;
            this.hasData = true;
        }
    }
    setProgress(percent) {
        if (this.progressBarElem && percent !== undefined && percent !== null) {
            this.progressBarElem.style.width = `${percent}%`;
            this.hasData = true;
        }
    }
    setStatus(text) {
        if (this.statusElem && text) {
            this.statusElem.textContent = text;
            this.hasData = true;
        }
    }
    finalize() {
        // Hide the container if nothing was set
        if (!this.hasData && this.container) {
            this.container.style.display = 'none';
        }
    }
}

class TaglineOverview {
    constructor(taglineSelector, overviewSelector) {
        this.taglineEl = document.querySelector(`[data="${taglineSelector}"]`);
        this.overviewEl = document.querySelector(`[data="${overviewSelector}"]`);
    }

    setTagline(text) {
        if (this.taglineEl) {
        this.taglineEl.textContent = text;
        }
    }

    setOverview(text) {
        if (this.overviewEl) {
        this.overviewEl.textContent = text;
        }
    }
}


class PageLoader {
    constructor(itemId) {
        this.id = itemId;
        this.background = new Background('backdrop-img');
        this.logo = new Logo('logo-img');
        this.genres = new Genres('item-genres');
        this.itemData = new ItemInfo('item-info');
        this.taglineOverview = new TaglineOverview('tagline', 'overview');
        this.videoData = new VideoData('.media-playback-container');
    }

    async load() {
        try {
            const [itemRes, ratingsRes, networksRes, videosRes, accountRes] = await Promise.all([
            apiFetch(`/content/v1/item/${this.id}`),
            apiFetch(`/content/v1/item/${this.id}/ratings`),
            apiFetch(`/content/v1/item/${this.id}/networks`),
            apiFetch(`/content/v1/item/${this.id}/videos`),
            apiFetch('/accounts/v1/l/a')
            ]);

            const [item, ratings, networks, videos, account] = await Promise.all([
            itemRes.json(),
            ratingsRes.json(),
            networksRes.json(),
            videosRes.json(),
            accountRes.json()
            ]);

            // if (videos.error) {
            //     window.location.href = '/404';
            // }

            // UI media updates
            this.background.setImage(item.backdrop_path || '');
            this.logo.setLogo(item.logos, item.original_title || item.title || 'No Logo Available');
            this.genres.load(item.genres);
            this.itemData.load(item, ratings, networks);
            this.taglineOverview.setTagline(item.tagline);
            this.taglineOverview.setOverview(item.overview);

            // UI media videos updates
            this.videoData.setEpisodeInfo(videos.episode_info);
            this.videoData.setDuration(videos.duration);
            this.videoData.setProgress(videos.progress);
            this.videoData.setStatus(videos.f);
            this.videoData.finalize(); // Hide if all values empty



            const accountMap = new Map(account.videos.map(v => [v.video_id, v]));
            const mergedVideos = videos.map(video => {
            const match = accountMap.get(video.id);
            if (match) {
                return { ...video, ...match };
            }
            return video;
            });
            next_ep(item.next_episode)
            // Load videos into UI
            loadVideos(this.id, mergedVideos, item.original_title || item.title || 'Untitled', item);
        } catch (err) {
            console.error('Error loading media item:', err);
            // window.location.href = '/404';
        }
    }  
}

function loadVideos(itemId, data, mediaTitle, item) {
    const videosContainer = document.querySelector(".videos-container");
    const seasonMenu = videosContainer.querySelector("#season-menu");
    const feedTitle = videosContainer.querySelector("[data='media-seasons']");

    seasonMenu.innerHTML = "";

    const isMovie = data.length === 1 && data[0].season_number == null;
    let groupedBySeason = {};

    if (isMovie) {
        groupedBySeason["1"] = data;
        feedTitle.innerHTML = `<h2>Movie: ${mediaTitle}</h2>`;
    } else {
    data.forEach(ep => {
        const season = ep.season_number;
        if (!groupedBySeason[season]) groupedBySeason[season] = [];
        groupedBySeason[season].push(ep);
    });
    const firstSeason = Math.min(...Object.keys(groupedBySeason));
    feedTitle.innerHTML = `<h2>S${firstSeason}: ${mediaTitle}</h2>`;
    }

    if (!isMovie) {
    Object.keys(groupedBySeason)
        .sort((a, b) => a - b)
        .forEach(season => {
        const btn = document.createElement("button");
        btn.className = "season-option";
        btn.dataset.season = season;
        btn.role = "menuitem";
        btn.textContent = `Season ${season}`;
        btn.addEventListener("click", () => {
            showSeason(season);
            feedTitle.innerHTML = `<h2>S${season}: ${mediaTitle}</h2>`;
            seasonMenu.classList.add("--hidden");
        });
        seasonMenu.appendChild(btn);
        });
    }

    const videosWrapper = videosContainer.querySelector(".videos-container > div:last-child");
    videosWrapper.innerHTML = "";

    Object.entries(groupedBySeason).forEach(([season, episodes], idx) => {
        const seasonContainer = document.createElement("div");
        seasonContainer.className = "video-panel-container";
        seasonContainer.dataset.mediaSeason = season;
        if (idx > 0) seasonContainer.classList.add("--hidden");

        episodes.forEach(ep => {

            const brightness = ep.watched ? '35%' : '100%';
            const progressPercent = ep.duration && ep.paused_at
                ? Math.min(100, Math.floor((ep.paused_at / ep.duration) * 100))
                : ep.watched ? 100 : 0;

            let progressText = '';
            if (ep.watched) {
                progressText = 'Watched';
            } else if (ep.paused_at && ep.duration) {
                const remaining = ep.duration - ep.paused_at;
                progressText = `${Math.floor(remaining / 60)} mins left`;
            }


            const a = document.createElement("a");
            a.href = `${itemId}/watch/${ep.id}`;
            a.className = "video_url";

            const mediaVideo = document.createElement("div");
            mediaVideo.className = "media-video";
            mediaVideo.dataset.id = ep.id;
            mediaVideo.dataset.date = ep.air_date || "";
            mediaVideo.dataset.duration = ep.metadata.duration || "";

            const videoCard = document.createElement("div");
            videoCard.className = "video-card";

            const img = document.createElement("img");
            img.src = `static/images/stills${ep.still_path || ep.metadata.key_frame}`;
            img.loading = "lazy";
            img.alt = "";
            img.style.filter = `brightness(${brightness})`;

            videoCard.appendChild(img);

            // ----------------------
            // Progress bar container
            // ----------------------
            if (ep.paused_at) {
                const progressBarContainer = document.createElement("div");
                progressBarContainer.className = "thumbnail-progress-bar";
                progressBarContainer.dataset.t = "progress-bar";

                const progressBar = document.createElement("div");
                progressBar.className = "progress-bar__progress";
                progressBar.style.width = `${progressPercent}%`;

                progressBarContainer.appendChild(progressBar);

                // Progress duration text
                const durationText = document.createElement("div");
                durationText.className = "thumbnail-progress-duration-text";
                durationText.dataset.t = "duration-info";
                durationText.textContent = progressText;

                // Watched checkmark (only if watched)
                let watchedDiv = null;
                if (ep.watched) {
                    watchedDiv = document.createElement("div");
                    watchedDiv.className = "thumbnail-progress-watched";
                    watchedDiv.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path fill-rule="evenodd" clip-rule="evenodd" 
                                d="M13.7071 1.29289C14.0976 1.68342 14.0976 2.31658 13.7071 2.70711L12.4053 4.00896C17.1877 4.22089 21 8.16524 21 13C21 17.9706 16.9706 22 12 22C7.02944 22 3 17.9706 3 13C3 12.4477 3.44772 12 4 12C4.55228 12 5 12.4477 5 13C5 16.866 8.13401 20 12 20C15.866 20 19 16.866 19 13C19 9.2774 16.0942 6.23349 12.427 6.01281L13.7071 7.29289C14.0976 7.68342 14.0976 8.31658 13.7071 8.70711C13.3166 9.09763 12.6834 9.09763 12.2929 8.70711L9.29289 5.70711C9.10536 5.51957 9 5.26522 9 5C9 4.73478 9.10536 4.48043 9.29289 4.29289L12.2929 1.29289C12.6834 0.902369 13.3166 0.902369 13.7071 1.29289Z" 
                                fill="#E8E8E8"/>
                        </svg>
                    `;
                }

                videoCard.appendChild(progressBarContainer);
                videoCard.appendChild(durationText);
                if (watchedDiv) videoCard.appendChild(watchedDiv);
            }


            mediaVideo.appendChild(videoCard);




            const videoText = document.createElement("div");
            videoText.className = "video-text feed-font-mobile";

            const mainInfo = document.createElement("div");
            mainInfo.className = "text-main-info";
            mainInfo.innerHTML = `
            <div class="video-text-a" data="media-title">${mediaTitle}</div>
            <div class="video-text-b --font-size-vbig" data="video-title">
                ${isMovie ? "" : `S${ep.season_number} E${ep.episode_number || 0}${ep.name ? " - " + ep.name : ""}`}
            </div>
            `;

            const moreInfo = document.createElement("div");
            moreInfo.className = "text-more-info";
            moreInfo.innerHTML = `
            <div class="video-text-c" data="resolution">${ep.metadata.resolution ? ep.metadata.resolution + " |" : ""}</div>
            <div class="video-text-c" data="resolution">${(ep.runtime ?? item.runtime) ? (ep.runtime ?? item.runtime) + " min |" : ""}</div>
            <div class="video-text-c" data="subtitles-available">${ep.subtitles.length > 0 ? "subtitles" : ""}</div>
            `;

            videoText.appendChild(mainInfo);
            videoText.appendChild(moreInfo);





            a.appendChild(mediaVideo);
            a.appendChild(videoText);
            seasonContainer.appendChild(a);
        });

        videosWrapper.appendChild(seasonContainer);
    });
}

function showSeason(season) {
    const panels = document.querySelectorAll(".video-panel-container");
    panels.forEach(panel => {
    if (panel.dataset.mediaSeason === season) {
        panel.classList.remove("--hidden");
    } else {
        panel.classList.add("--hidden");
    }
    });
}  


function waitForNonLazyImages() {
  const images = document.body.querySelectorAll('img:not([loading="lazy"])');
  const promises = [];

  images.forEach(img => {
    if (img.complete && img.naturalHeight !== 0) {
      return;
    }
    promises.push(new Promise(resolve => {
      img.onload = () => resolve();
      img.onerror = () => resolve();
    }));
  });

  return Promise.all(promises);
}

async function waitForImagesWithTimeout(timeout = 3000) {
  const waitPromise = waitForNonLazyImages();
  const timeoutPromise = new Promise(resolve => setTimeout(resolve, timeout));
  await Promise.race([waitPromise, timeoutPromise]);
}


function collapseToggle() {
    document.querySelectorAll('.collapsable').forEach(container => {
        const btn = container.querySelector('.see-more-btn');
        if (!btn) return;

        const collapsedElements = container.querySelectorAll('[collapsed]');
        let hasOverflow = false;

        collapsedElements.forEach(el => {
            el.classList.remove('collapsed');
            el.setAttribute('collapsed', 'false');

            const style = getComputedStyle(el);
            const maxHeightPx = parseFloat(style.fontSize) * 20; 
            const actualHeight = el.offsetHeight;

            if (actualHeight > maxHeightPx) {
            el.classList.add('collapsed');
            el.setAttribute('collapsed', 'true');
            hasOverflow = true;
            }
            // DEBUG
            // console.log('el', el);
            // console.log('offsetHeight', el.offsetHeight);
            // console.log('offsetWidth', el.offsetWidth);
            // console.log('display', getComputedStyle(el).display);
            // console.log('visibility', getComputedStyle(el).visibility);
        });

        btn.style.display = hasOverflow ? 'inline-block' : 'none';

        btn.addEventListener('click', () => {
            collapsedElements.forEach(el => {
            if (el.getAttribute('collapsed') === 'true') {
                el.classList.remove('collapsed');
                el.setAttribute('collapsed', 'false');
                btn.textContent = 'See less';
            } else {
                el.classList.add('collapsed');
                el.setAttribute('collapsed', 'true');
                btn.textContent = 'See more';
            }
            });
        });
    });    
}

async function next_ep(data) {
    if (data && Object.keys(data).length > 0) {
        const nextEpBanner = document.createElement('div')
        nextEpBanner.classList.add("next-episode-banner");

        nextEpBanner.innerHTML = `
            <h3>Next Episode</h3>
            <p><strong>${data.name}</strong></p>
            <p>S${data.season_number} • E${data.episode_number}</p>
            <p>${data.air_date}</p>
        `;


        nextEpBanner.addEventListener("click", () => {
            nextEpBanner.style.display = "none";
        });

        const container = document.getElementById("m-content");
        if (container) {
            container.appendChild(nextEpBanner);
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const path = window.location.pathname;
    const id = parseInt(path.slice(1), 10);
    if (isNaN(id)) {
        console.error('Invalid item id');
        return;
    }
    const mediaLoader = new PageLoader(id);
    await mediaLoader.load();



    // Wait up to 2000ms for images to load to ensure the UI displays correctly
    await waitForImagesWithTimeout(2000);
    const _overlay = document.getElementById('loading-overlay');
    const _app = document.querySelector('.app-layout'); 
    if (_app) _app.classList.remove('app-layout--hidden'); // Show the main app layout by removing the hidden class
    if (_overlay) _overlay.style.display = 'none'; // Hide the loading overlay after content is ready


    // "See more" / "See less"
    collapseToggle()    

    // Initial sort
    sortVideos("oldest");
});


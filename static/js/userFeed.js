import { apiFetch } from './api/_api.js';

async function renderCatalog(data, element) { 
    const container = document.getElementById(element);
    container.innerHTML = ''; 
    data.forEach(item => {
        const title = item.original_name || item.title;
        const posterPath = item.poster_path
            ? `/static/images/posters/${item.poster_path.replace(/^\//, '')}`
            : '/static/images/default_poster.jpg';

        const poster = document.createElement('div');
        poster.className = 'poster';
        poster.id = item.id;
        poster.setAttribute('data-date', item.entry_updated || '');
        poster.setAttribute('title', title);

        poster.innerHTML = `
            <a href="${item.id}" class="poster__link">
                <img src="${posterPath}" loading="lazy" alt="${title}" 
                    onload="if (this.src.includes('default_poster.jpg')) this.nextElementSibling?.classList.remove('hidden');" 
                    onerror="this.onerror=null; this.src='/static/images/default_poster.jpg'; this.nextElementSibling?.classList.remove('hidden');">
                <div class="poster-fallback-title hidden">${title}</div>
            </a>
        `;
        container.appendChild(poster);
    });
}


async function renderHeroCards(data, elementId) {
    const heroSection = document.getElementById('hero');
    const container = document.getElementById(elementId);
    container.innerHTML = ''; 

    if (!data || !data.length) {
        heroSection.style.display = 'none'; 
        return;
    }

    heroSection.style.display = 'block'; 
    const dotsContainer = document.getElementById('hero-dots');
    dotsContainer.innerHTML = ''; 




    const filteredData = [];
    const seen = {}; // { media_id: item }
    
    for (const item of data) {
      const mediaId = item.media_id;
    
      // If media_id haven't seen yet, or item is more recent
      if (!seen[mediaId] || item.entry_updated > seen[mediaId].entry_updated) {
        seen[mediaId] = item;
      }
    }
    
    for (const key in seen) {
      filteredData.push(seen[key]);
    }

    filteredData.sort((a, b) => new Date(b.entry_updated) - new Date(a.entry_updated));
    const FiveVids = filteredData.slice(0, 5);

    FiveVids.forEach((item, index) => {
        const title = item.name || 'Untitled';
        const SeasonEp = item.season_number ? `S${item.season_number}: Episode ${item.episode_number || 0}` : null;

        const still = (item.still_path || (item.metadata && item.metadata.key_frame))
            ? `/static/images/stills${(item.still_path || item.metadata.key_frame)}`
            : '/static/images/default_poster.jpg';

        const brightness = item.watched ? '35%' : '100%';
        const progressPercent = item.duration && item.paused_at
            ? Math.min(100, Math.floor((item.paused_at / item.duration) * 100))
            : item.watched ? 100 : 0;

        let progressText = '';
        if (item.watched) {
            progressText = 'Watched';
        } else if (item.paused_at && item.duration) {
            const remaining = item.duration - item.paused_at;
            progressText = `${Math.floor(remaining / 60)} mins left`;
        }

        const card = document.createElement('a');
        card.className = 'card animate-in';
        card.href = `${item.media_id}/watch/${item.id}`
        card.setAttribute('item-id', item.media_id);
        card.setAttribute('video-id', item.id);

        card.innerHTML = `
            <div class="image-wrapper">
                <div class="hero-poster">
                    <div class="hero-poster__img">
                        <img src="${still}" alt="${title}" style="filter: brightness(${brightness});" onerror="this.onerror=null; this.src='/static/images/default_poster.jpg';">
                    </div>
                    <div class="thumbnail-progress-bar" data-t="progress-bar">
                        <div class="progress-bar__progress" style="width: ${progressPercent}%;"></div>
                    </div>
                    <div class="thumbnail-progress-duration-text" data-t="duration-info">${progressText}</div>
                    ${item.watched ? `
                    <div class="thumbnail-progress-watched">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path fill-rule="evenodd" clip-rule="evenodd" d="M13.7071 1.29289C14.0976 1.68342 14.0976 2.31658 13.7071 2.70711L12.4053 4.00896C17.1877 4.22089 21 8.16524 21 13C21 17.9706 16.9706 22 12 22C7.02944 22 3 17.9706 3 13C3 12.4477 3.44772 12 4 12C4.55228 12 5 12.4477 5 13C5 16.866 8.13401 20 12 20C15.866 20 19 16.866 19 13C19 9.2774 16.0942 6.23349 12.427 6.01281L13.7071 7.29289C14.0976 7.68342 14.0976 8.31658 13.7071 8.70711C13.3166 9.09763 12.6834 9.09763 12.2929 8.70711L9.29289 5.70711C9.10536 5.51957 9 5.26522 9 5C9 4.73478 9.10536 4.48043 9.29289 4.29289L12.2929 1.29289C12.6834 0.902369 13.3166 0.902369 13.7071 1.29289Z" fill="#E8E8E8"/>
                        </svg>
                    </div>` : ''}
                </div>
            </div>
            <div class="hero-text">
                ${SeasonEp ? `<div class="h-title"><p>${SeasonEp}</p></div>` : '<div class="h-title"><p>Movie</p></div>'}
                <div class="title" title="${title}"><h3>${title}</h3></div>
            </div>
        `;

        container.appendChild(card);

        // Create dot for nav
        const dot = document.createElement('div');
        dot.className = 'dot';
        dot.dataset.index = index;
        dot.innerHTML = `<svg width="12px" height="12px" viewBox="0 0 12 12">
                            <circle fill="currentColor" cx="6" cy="6" r="6"></circle>
                         </svg>`;
        dotsContainer.appendChild(dot);
    });

    // Dot nav
    const dots = dotsContainer.querySelectorAll('.dot');
    const scroller = document.getElementById('hero-sl');
    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            const idx = parseInt(dot.dataset.index);
            const cardWidth = scroller.children[0].offsetWidth;
            scroller.scrollTo({ left: cardWidth * idx, behavior: 'smooth' });
        });
    });
}


async function loadItem(id) {
    const item = await apiFetch(`/content/v1/item/${id}`)
    const data = await item.json()
    return data    
}

async function loadCatalog(data) {
    const promises = data.map(item => loadItem(item.media_id))
    const catalog = await Promise.all(promises)
    catalog.sort((a, b) => new Date(b.new_video_inserted) - new Date(a.new_video_inserted));
    return catalog
}




async function loadVideo(id) {
    const item = await apiFetch(`/content/v1/video/${id}`)
    const data = await item.json()
    return data    
}

async function loadContinueFeed(data) {
    const promises = data.map(async item => {
        const apiResult = await loadVideo(item.video_id);
        return { ...item, ...apiResult }; // merge API result into original item
    });

    const catalog = await Promise.all(promises);
    catalog.sort((a, b) => new Date(b.entry_updated) - new Date(a.entry_updated));
    return catalog;
}




async function loadFeed() {
    const res = await apiFetch('/accounts/v1/l/a'); 
    const data = await res.json();

    const catalog = await loadCatalog(data.library)
    const videos = await loadContinueFeed(data.videos)

    renderHeroCards(videos, 'hero-sl')
    renderCatalog(catalog, 'user-new');
}



document.addEventListener('DOMContentLoaded', async () => {
    loadFeed();
});

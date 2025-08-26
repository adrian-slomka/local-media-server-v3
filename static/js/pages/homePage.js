import { apiFetch } from '../api/_api.js';

function renderCatalog(data, element) { 
    const container = document.getElementById(element);
    container.innerHTML = ''; 
    data.forEach(item => {
        const title = item.original_name || item.title || 'Untitled';
        const posterPath = item.poster_path
            ? `/static/images/posters/${item.poster_path.replace(/^\//, '')}`
            : '/static/images/default_poster.jpg';

        const poster = document.createElement('div');
        poster.className = 'poster';
        poster.id = item.id;
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

async function fetchCatalog() {
    const res = await apiFetch('/content/v1/catalog'); 
    const data = await res.json();

    renderCatalog(data, 'new-carousel');
}

async function fetchTv() {
    const res = await apiFetch('/content/v1/tv');  
    const data = await res.json();

    renderCatalog(data, 'tv-carousel');
}

async function fetchMovies() {
    const res = await apiFetch('/content/v1/movies'); 
    const data = await res.json();

    renderCatalog(data, 'movie-carousel');
}

document.addEventListener('DOMContentLoaded', async () => {
    fetchCatalog();
    fetchTv();
    fetchMovies();
});

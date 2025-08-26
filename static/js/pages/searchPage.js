import { apiFetch } from '../api/_api.js';

let debounceTimer;

function searchFunction() {
    const query = document.getElementById("search-item").value;
    clearTimeout(debounceTimer);

    debounceTimer = setTimeout(() => {
        if (query.length > 0) {
            apiFetch('content/v1/search?query=' + encodeURIComponent(query))
                .then(response => response.json())
                .then(data => {
                    const resultsContainer = document.getElementById("search-results");
                    resultsContainer.innerHTML = '';

                    if (data.results.length > 0) {
                        data.results.forEach(result => {
                            const title = result.original_name || result.title || 'Untitled';
                            const posterPath = result.poster_path
                                ? `/static/images/posters/${result.poster_path.replace(/^\//, '')}`
                                : '/static/images/default_poster.jpg';

                            const poster = document.createElement('div');
                            poster.className = 's-poster';
                            poster.id = result.id;
                            poster.setAttribute('data-p', 'xxxx00');
                            poster.setAttribute('title', title);

                            poster.innerHTML = `
                                <a href="${result.id}" class="poster__link">
                                    <img src="${posterPath}" loading="lazy" alt="${title}" 
                                        onload="if (this.src.includes('default_poster.jpg')) this.nextElementSibling?.classList.remove('hidden');" 
                                        onerror="this.onerror=null; this.src='/static/images/default_poster.jpg'; this.nextElementSibling?.classList.remove('hidden');">
                                    <div class="poster-fallback-title-search hidden">${title}</div>
                                </a>
                            `;

                            resultsContainer.appendChild(poster);
                        });
                    } else {
                        resultsContainer.innerHTML = `<p>No results found for "${query}"</p>`;
                    }
                })
                .catch(error => console.error('Error fetching search results:', error));
        } else {
            document.getElementById("search-results").innerHTML = '';
        }
    }, 500);
}

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("search-item");
    if (searchInput) {
        searchInput.addEventListener("keyup", searchFunction);
    }
});

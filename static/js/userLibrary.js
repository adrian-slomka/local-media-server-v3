import { apiFetch } from './api/_api.js';



async function setWatchlistButton(id, watchlisted) {
    const watchlistButton = document.getElementById("watchlist");

    if (!watchlistButton || watchlisted === undefined) {
        return;
    }    

    // Apply initial state
    if (watchlisted === 1) {
        watchlistButton.classList.add('i-icon-active');
    } else {
        watchlistButton.classList.remove('i-icon-active');
    }

    // Toggle on click
    watchlistButton.addEventListener("click", () => {
        watchlisted = watchlisted === 1 ? 0 : 1;
        watchlistButton.classList.toggle("i-icon-active", watchlisted === 1);

        apiFetch(`/accounts/v1/l`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ 'media_id': id, 'watchlisted': watchlisted }) });
    });  
}


document.addEventListener("DOMContentLoaded", async function () {
    const path = window.location.pathname; // "/12"
    const parts = path.split('/');          // ["", "12"]
    const itemId = parseInt(parts[1], 10);  // MediaItem.id 12

    

    if (isNaN(itemId)) {
        console.error('Invalid IDs');
        return
    }

    const data = await apiFetch(`/accounts/v1/l?id=${itemId}`).then(res => res.json());

    setWatchlistButton(itemId, data.watchlisted)

});
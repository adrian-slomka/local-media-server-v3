import { apiFetch } from '../api/_api.js';


function removeId(itemId) {
    apiFetch('/content/v1/d', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            media_id: parseInt(itemId, 10),
        })
    })
    .then(async (response) => {
        const data = await response.json();

        if (response.ok && !data.error) {
            console.log('Item deleted, redirecting...');
            window.location.href = '/';
        } else {
            console.error('Server returned error:', data.error || 'Unknown error');
            alert(`Failed to delete item: ${data.error || 'Unknown error'}`);
        }
    })
    .catch(err => console.error('Network or fetch error:', err));
}

function requestData(itemId, category, title, year) {
    apiFetch('/content/v1/r', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            media_id: parseInt(itemId, 10),
            category: category,  // "tv" or "movie"
            title: title,     // required
            year: year || null,       // optional
        })
    })
    .then(() => {
        console.log('Request sent successfully');
        alert(`Attempting to fetch data for category: ${category}, title: ${title}, year: ${year || 'N/A'}`);
    })
    .catch(err => console.error('error sending request:', err));
}

document.addEventListener("DOMContentLoaded", async function () {
    const path = window.location.pathname; // "/12"
    const parts = path.split('/');          // ["", "12"]
    const itemId = parseInt(parts[1], 10);  // MediaItem.id 12

    

    if (isNaN(itemId)) {
        console.error('Invalid IDs');
        return
    }


    const deleteBtn = document.getElementById('delete-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this item?')) {
                removeId(itemId);
            }
        });
    }


    // Request button
    const requestBtn = document.getElementById('request-btn');
    if (requestBtn) {
        requestBtn.addEventListener('click', () => {
            const category = prompt('Enter category ("tv" or "movie"):', 'movie');
            const title = prompt('Enter title of the item:');
            const year = prompt('Enter year (optional):');

            if (!title || !category) {
                alert('Category and title are required!');
                return;
            }

            requestData(itemId, category, title, year || null);
        });
    }


});
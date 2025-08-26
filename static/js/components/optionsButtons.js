import { apiFetch } from '../api/_api.js';

function showStatus(message) {
    const statusEl = document.createElement('div');

    Object.assign(statusEl.style, {
        position: 'fixed',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        padding: '10px 20px',
        backgroundColor: '#333',
        color: '#fff',
        borderRadius: '5px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
        zIndex: 9999,
        fontFamily: 'sans-serif',
        fontSize: '14px',
        opacity: 0,
        transition: 'opacity 0.3s ease',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
    });

    // Message text
    const textNode = document.createElement('span');
    textNode.textContent = message;
    statusEl.appendChild(textNode);

    document.body.appendChild(statusEl);
    requestAnimationFrame(() => {statusEl.style.opacity = 1;});

    return { statusEl, textNode };
}

async function requestData(itemId, category, title, year) {
    const { statusEl, textNode } = showStatus('Request queued...');
    
    try {
        const response = await apiFetch('/content/v1/r', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ media_id: itemId, category, title, year: year || null })
        });

        const data = await response.json();
        if (!response.ok || data.error) {
            alert(`Failed to start request: ${data.error || 'Unknown error'}`);
            return;
        }

        const jobId = data.job_id;
        let secondsElapsed = 0;

        // Poll job status every 3 seconds
        const interval = setInterval(async () => {
            secondsElapsed += 3;
            textNode.textContent = `Request in progress... ${secondsElapsed} sec`;

            const statusResp = await apiFetch(`/status/v1/${jobId}`);
            const statusData = await statusResp.json();

            if (statusData.status === 'done') {
                clearInterval(interval);
                alert('TMDB data successfully fetched!');
                removeStatusOverlay(statusEl);
                window.location.reload();
            } else if (statusData.status === 'error') {
                clearInterval(interval);
                alert(`Request failed: ${statusData.error}`);
                removeStatusOverlay(statusEl);
            }
        }, 3000);

    } catch (err) {
        console.error('Network or fetch error:', err);
        alert('Network error while sending request.');
        removeStatusOverlay(statusEl);
    }
}

function removeStatusOverlay(el) {
    el.style.opacity = 0;
    el.addEventListener('transitionend', () => el.remove());
}


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
import { apiFetch } from '../api/_api.js';

export function trackTime(player, itemId, videoId) {
    const SEND_INTERVAL = 15000; // send every 15s
    let lastSentTime = 0
    let accumulatedTime = 0;
    let lastCheckTime = Date.now();

    const sendWatchtime = () => {
        const currentTime = Math.floor(player.currentTime());
        apiFetch('/accounts/v1/w', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                media_id: parseInt(itemId, 10),
                video_id: parseInt(videoId, 10),
                pausedAt: currentTime,
                videoDuration: Math.floor(player.duration()),
                secondsPlayed: accumulatedTime
            })
        }).catch(err => console.error('error sending watchtime data:', err));

        accumulatedTime = 0;
        lastSentTime = currentTime;        
    };

    setInterval(() => {
        if (!player.paused() && !player.ended()) {
            const now = Date.now();
            const delta = Math.floor((now - lastCheckTime) / 1000);
            if (delta > 0) {
                accumulatedTime += delta;
                lastCheckTime = now;
            } 
        } else {
            lastCheckTime = Date.now(); 
        }
    }, 1000);
    
    setInterval(() => {
        if (accumulatedTime > 0) sendWatchtime();
    }, SEND_INTERVAL);

    player.on('ended', () => sendWatchtime(Math.floor(player.currentTime())));
}

export function setTime(player, startTime) {
    let timeSet = false;

    player.on('play', () => {
        if (!timeSet && startTime > 0) {
            try {
                player.currentTime(startTime);
                timeSet = true;
            } catch (e) {
                console.warn('Seeking failed on play, waiting for canplay...');
            }
        }
    });

    player.on('canplay', () => {
        if (!timeSet && startTime > 0) {
            player.currentTime(startTime);
            timeSet = true;
        }
    });
}

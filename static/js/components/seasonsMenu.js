document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('season-toggle');
    const menu = document.getElementById('season-menu');
    const seasonOptions = menu.querySelectorAll('.season-option');
    const videoPanels = document.querySelectorAll('.video-panel-container[data="media-season"]');
    const titleElement = document.querySelector('.feed-header__title h2');

    toggleBtn.addEventListener('click', () => {
    const isHidden = menu.classList.contains('--hidden');
    menu.classList.toggle('--hidden');
    toggleBtn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
    });

    seasonOptions.forEach(btn => {
    btn.addEventListener('click', () => {
        const selectedSeason = btn.dataset.season;

        seasonOptions.forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        menu.classList.add('--hidden');
        toggleBtn.setAttribute('aria-expanded', 'false');

        videoPanels.forEach(panel => {
        if (panel.dataset.t === selectedSeason) {
            panel.classList.remove('--hidden');
        } else {
            panel.classList.add('--hidden');
        }
        });

        titleElement.textContent = `S${selectedSeason}:`;
    });
    });

    document.addEventListener('click', (e) => {
    if (!toggleBtn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('--hidden');
        toggleBtn.setAttribute('aria-expanded', 'false');
    }
    });
});
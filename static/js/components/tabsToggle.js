// TABS HANDLER

document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll('.tab'); // all tab content divs
    const hero = document.getElementById('hero');    // hero element
    const navItems = document.querySelectorAll('.nav-t'); // nav buttons

    function highlight(idToHighlight) {
        navItems.forEach(el => el.classList.remove('--highlight'));
        const el = document.getElementById(idToHighlight);
        if (el) el.classList.add('--highlight');
    }

    function showTab(id) {
        tabs.forEach(tab => {
            tab.style.display = (tab.id === id) ? 'block' : 'none';
        });
    }

    function setHeroVisible(visible) {
        if (hero) hero.style.display = visible ? 'block' : 'none';
    }

    function activateTab(navId) {
        switch (navId) {
            case 'featured':
                setHeroVisible(true);
                showTab('feat-tab');
                break;
            case 'browse':
                setHeroVisible(false);
                showTab('browse-tab');
                break;
            case 'search':
                setHeroVisible(false);
                showTab('search-tab');
                break;
            case 'watchlist':
                setHeroVisible(false);
                showTab('watchlist-tab');
                break;
            default:
                setHeroVisible(true);
                showTab('feat-tab');
                navId = 'featured';
                break;
        }
        highlight(navId);
        // sessionStorage.setItem('selectedNavTab', navId);
    }

    // // Load saved tab or default
    // const savedTab = sessionStorage.getItem('selectedNavTab') || 'featured';
    // activateTab(savedTab);

    // Add click handlers
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            activateTab(item.id);
        });
    });
});

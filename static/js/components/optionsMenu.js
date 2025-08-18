document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById('options-toggle');
    const menu = document.getElementById('options-menu');
    const seasonOptions = menu.querySelectorAll('.i-option');

    toggleBtn.addEventListener('click', () => {
    const isHidden = menu.classList.contains('--hidden');
    menu.classList.toggle('--hidden');
    toggleBtn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
    });

    document.addEventListener('click', (e) => {
    if (!toggleBtn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('--hidden');
        toggleBtn.setAttribute('aria-expanded', 'false');
    }
    });
}); 
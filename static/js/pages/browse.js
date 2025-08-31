import { apiFetch } from '../api/_api.js';

async function fetchLibrary() {
    try {
        const response = await apiFetch('/content/v1/index');
        const data = await response.json();
        return data; // expects { A: [{id, title}], B: [...], ... }
    } catch (err) {
        console.error('Failed to fetch library:', err);
        return {};
    }
}

function renderAlphabet(library, onSelect) {
    const container = document.getElementById('alphabet');
    container.innerHTML = '';
    const letters = Object.keys(library).sort();

    letters.forEach(letter => {
        const btn = document.createElement('button');
        btn.textContent = letter;
        btn.style.fontSize = '2rem'
        btn.addEventListener('click', () => {
        document.querySelectorAll('.alphabet button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        onSelect(letter);
        });
        container.appendChild(btn);
    });
}

function renderTitles(library, letter) {
    const list = document.getElementById('title-list');
    list.innerHTML = '';
    if (!library[letter]) return;
    
    library[letter].forEach(item => {
        const li = document.createElement('li');

        const a = document.createElement('a');
        a.textContent = `${item.title} ⠀ [ ${item.category.toUpperCase()} ]`;
        a.href = `/${item.id}`;
        a.style.textDecoration = 'none';
        a.style.color = '#dadadaff';
        a.style.fontSize = '2.2rem'

        li.appendChild(a);
        list.appendChild(li);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    const library = await fetchLibrary();

    renderAlphabet(library, letter => {
      renderTitles(library, letter);
    });
  
    const firstLetter = Object.keys(library)[0];
    if (firstLetter) {
      renderTitles(library, firstLetter);
      document.querySelectorAll('.alphabet button')[0].classList.add('active');
    }
});
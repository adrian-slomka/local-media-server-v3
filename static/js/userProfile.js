import { apiFetch } from './api/_api.js';

function userProfile(name, picture) {
    document.getElementById('profile-name').textContent = name;
    document.getElementById('profile-picture').src = picture;    
}

document.addEventListener('DOMContentLoaded', async () => {
    const savedUsername = sessionStorage.getItem('username');
    const savedUserPicture = sessionStorage.getItem('userPicture');

    try {
        const response = await apiFetch('/accounts/v1/me');
        const data = await response.json();

        const username = data.profile;
        const profilePicture = `/static/images/profiles/${data.profile_picture}`;

        if (username !== savedUsername) {
            sessionStorage.setItem('username', username);
        }
        if (profilePicture !== savedUserPicture) {
            sessionStorage.setItem('userPicture', profilePicture);
        }

        userProfile(username, profilePicture);

    } catch (error) {
        console.error('Error fetching profile:', error);

        if (savedUsername && savedUserPicture) {
            userProfile(savedUsername, savedUserPicture);
        }
    }
});

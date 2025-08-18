export function captionPreference(player) {
    let suppressChange = true;

    function saveCaptionPreference(enabled, lang) {
        localStorage.setItem('captions_enabled', enabled ? 'true' : 'false');
        localStorage.setItem('captions_lang', lang || '');
    }

    function applyCaptionPreference() {
        suppressChange = true;
        const enabled = localStorage.getItem('captions_enabled') === 'true';
        const lang = localStorage.getItem('captions_lang');

        const textTracks = player.textTracks();
        for (let i = 0; i < textTracks.length; i++) {
            if (enabled && textTracks[i].language === lang) {
                textTracks[i].mode = 'showing';
                break;
            } else {
                textTracks[i].mode = 'disabled';
            }
        }
        suppressChange = false;
    }

    player.on('texttrackchange', () => {
        if (suppressChange) {
            return
        }
        const textTracks = player.textTracks();
        let enabled = false;
        let lang = '';

        for (let i = 0; i < textTracks.length; i++) {
            if (textTracks[i].mode === 'showing') {
                enabled = true;
                lang = textTracks[i].language;
                break;
            }
        }

        saveCaptionPreference(enabled, lang);
    });

    player.on('loadedmetadata', applyCaptionPreference);
}
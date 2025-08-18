export async function apiFetch(url, options = {}) {
    await window.tokenReady;

    options.headers = {
        ...(options.headers || {}),
        "Authorization": `Bearer ${window.accessToken}`
    };

    let res = await fetch(url, options);

    return res;
}
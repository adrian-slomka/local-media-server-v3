let accessToken = null;
let tokenExpiry = 0;

async function fetchNewToken() {
    const tokenRes = await fetch("/auth/v1/token");
    const tokenData = await tokenRes.json();

    accessToken = tokenData.access_token;
    tokenExpiry = Date.now() + (tokenData.expires_in * 1000) - 5000;
    window.accessToken = accessToken;
}

async function getToken() {
    const now = Date.now();
    if (!accessToken || now >= tokenExpiry) {
        await fetchNewToken();
    }
    return accessToken;
}

window.tokenReady = (async () => {
    await fetchNewToken();
})();

setInterval(async () => {
    await getToken();
}, 30000);

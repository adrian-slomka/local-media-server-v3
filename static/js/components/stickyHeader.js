document.addEventListener("DOMContentLoaded", function () {
    const header = document.querySelector('.app-layout__header');
    const rootStyles = getComputedStyle(document.documentElement);

    function parseCssValue(value) {
    if (value.endsWith('vh')) {
        return window.innerHeight * parseFloat(value) / 100;
    } else if (value.endsWith('rem')) {
        const remInPx = parseFloat(getComputedStyle(document.documentElement).fontSize);
        return parseFloat(value) * remInPx;
    } else if (value.endsWith('px')) {
        return parseFloat(value);
    }
    return 0;
    }

    const headerHeight = parseCssValue(rootStyles.getPropertyValue('--HEADER-WIDTH'));
    const headerMarginTop = parseCssValue(rootStyles.getPropertyValue('--HEADER-MARGIN-TOP'));
    const revealThreshold = headerHeight + headerMarginTop - 100;

    window.addEventListener('scroll', () => {
    if (window.scrollY <= revealThreshold) {
        header.classList.remove('header--hidden');
    } else {
        header.classList.add('header--hidden');
    }
    });    
});
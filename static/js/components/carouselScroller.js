document.addEventListener('DOMContentLoaded', () => {
    const SCROLL_AMOUNT = 1000;

    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        const carousel = wrapper.querySelector('.wide-cards-carousel');
        const leftArrow = wrapper.querySelector('.arrow-button-l');
        const rightArrow = wrapper.querySelector('.arrow-button-r');

        if (carousel && leftArrow && rightArrow) {
            leftArrow.addEventListener('click', () => {
                carousel.scrollBy({ left: -SCROLL_AMOUNT, behavior: 'smooth' });
            });

            rightArrow.addEventListener('click', () => {
                carousel.scrollBy({ left: SCROLL_AMOUNT, behavior: 'smooth' });
            });
        }
    });
});
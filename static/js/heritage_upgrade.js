
document.addEventListener("DOMContentLoaded", () => {

    const elements = document.querySelectorAll(
        ".heritage-reveal"
    );

    if (
        !("IntersectionObserver" in window) ||
        window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches
    ) {
        elements.forEach(element => {
            element.classList.add("is-visible");
        });

        return;
    }

    const observer = new IntersectionObserver(
        (entries, currentObserver) => {

            entries.forEach(entry => {

                if (entry.isIntersecting) {
                    entry.target.classList.add(
                        "is-visible"
                    );

                    currentObserver.unobserve(
                        entry.target
                    );
                }

            });

        },
        {
            threshold: 0.12
        }
    );

    elements.forEach(element => {
        observer.observe(element);
    });

});

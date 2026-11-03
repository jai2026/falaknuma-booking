
// ==================================
// 1. MOBILE NAVIGATION
// ==================================

const menuToggle = document.getElementById("menuToggle");
const navLinks = document.querySelector(".nav-links");

menuToggle.addEventListener("click", function () {
    navLinks.classList.toggle("active");

    menuToggle.textContent =
        navLinks.classList.contains("active") ? "✕" : "☰";
});


// Close mobile navigation after clicking a link

document.querySelectorAll(".nav-links a").forEach(function (link) {

    link.addEventListener("click", function () {
        navLinks.classList.remove("active");
        menuToggle.textContent = "☰";
    });

});


// ==================================
// 2. DATE ELEMENTS
// ==================================

const checkin = document.getElementById("checkin");
const checkout = document.getElementById("checkout");


// Get today's date in local time

function getToday() {

    const today = new Date();

    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


// Set minimum date

checkin.min = getToday();
checkout.min = getToday();


// ==================================
// 3. CHECKOUT DATE VALIDATION
// ==================================

checkin.addEventListener("change", function () {

    if (!checkin.value) return;

    const nextDay = new Date(checkin.value + "T00:00:00");

    nextDay.setDate(nextDay.getDate() + 1);

    const year = nextDay.getFullYear();
    const month = String(nextDay.getMonth() + 1).padStart(2, "0");
    const day = String(nextDay.getDate()).padStart(2, "0");

    const minimumCheckout = `${year}-${month}-${day}`;

    checkout.min = minimumCheckout;

    if (!checkout.value || checkout.value < minimumCheckout) {
        checkout.value = minimumCheckout;
    }

});


// ==================================
// 4. RESERVATION FORM
// ==================================

const reservationForm = document.getElementById("reservationForm");

reservationForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const checkin = document.getElementById("checkin").value;
    const checkout = document.getElementById("checkout").value;

    if (checkin && checkout) {
        alert("Checking availability...");
    }
});

    if (departure <= arrival) {

        bookingMessage.textContent =
            "Departure date must be after arrival date.";

        return;

    }

    const arrivalDate = new Date(arrival + "T00:00:00");
    const departureDate = new Date(departure + "T00:00:00");

    const nights = Math.round(
        (departureDate - arrivalDate) / (1000 * 60 * 60 * 24)
    );

    bookingMessage.textContent =
        `Your search: ${nights} night(s), ${guests} guest(s). ` +
        "Room availability will be enabled in Phase 4.";

;


// ==================================
// 5. SET DEFAULT CHECK-IN DATE
// ==================================

checkin.value = getToday();

checkin.dispatchEvent(new Event("change"));

"use strict";

document.addEventListener("DOMContentLoaded", function () {

    // Mobile navigation
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");

    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", function () {
            const isOpen = navLinks.classList.toggle("open");

            menuToggle.setAttribute("aria-expanded", String(isOpen));
            menuToggle.textContent = isOpen ? "✕" : "☰";
        });
    }

    // Automatically hide notification messages
    document.querySelectorAll(".message").forEach(function (message) {
        window.setTimeout(function () {
            message.style.transition = "opacity 0.4s";
            message.style.opacity = "0";

            window.setTimeout(function () {
                message.remove();
            }, 400);
        }, 5000);
    });

    // Prevent invalid quantities on quantity inputs
    document.querySelectorAll('input[name="quantity"]').forEach(function (input) {
        input.addEventListener("change", function () {
            const minimum = Number(input.min || 1);
            const value = Number(input.value);

            if (!Number.isFinite(value) || value < minimum) {
                input.value = minimum;
            }
        });
    });

});
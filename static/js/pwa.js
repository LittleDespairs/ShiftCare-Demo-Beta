(function () {
    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/service-worker.js").then(function (registration) {
            return registration.update();
        }).catch(function () {
            // The app still works normally when service workers are unavailable.
        });
    });
})();

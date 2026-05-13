self.addEventListener("push", function (event) {
    let payload = {
        title: "SpielplatzAtlas",
        message: "Neue Systemnachricht",
        url: "/internal/notifications/"
    };

    if (event.data) {
        try {
            payload = event.data.json();
        } catch (error) {
            payload.message = event.data.text();
        }
    }

    const options = {
        body: payload.message,
        data: {
            url: payload.url || "/internal/notifications/",
            notificationId: payload.notification_id || null
        },
        tag: payload.notification_id ? `system-notification-${payload.notification_id}` : "spielplatz-atlas",
        renotify: true
    };

    event.waitUntil(
        self.registration.showNotification(payload.title || "SpielplatzAtlas", options)
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();

    const targetUrl = event.notification.data && event.notification.data.url
        ? event.notification.data.url
        : "/internal/notifications/";

    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
            for (const client of clientList) {
                if (client.url === targetUrl && "focus" in client) {
                    return client.focus();
                }
            }

            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
            return null;
        })
    );
});

// Service worker mínimo: solo habilita la instalación como PWA.
// No cachea nada a propósito, para que los datos (precios, álbum) siempre
// se vean frescos y no haya que lidiar con invalidación de caché.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());
self.addEventListener("fetch", () => {});

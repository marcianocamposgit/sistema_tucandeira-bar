/* Tucandeira Rock Bar — service worker mínimo.

   Existe só para o navegador permitir "Instalar app" / "Adicionar à tela
   inicial". Não guarda nada em cache: o sistema não funciona offline, todo
   pedido vai direto ao servidor do bar. Servido em /sw.js (raiz), para
   valer para o site inteiro. */
self.addEventListener('install', function () {
    self.skipWaiting();
});

self.addEventListener('activate', function (evento) {
    evento.waitUntil(self.clients.claim());
});

// Sem respondWith(): o navegador busca tudo na rede, como se o service worker
// não existisse. (Chrome antigo exige um evento fetch para oferecer a instalação.)
self.addEventListener('fetch', function () {});

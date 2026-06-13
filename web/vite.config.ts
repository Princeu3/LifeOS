import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "LifeOS",
        short_name: "LifeOS",
        theme_color: "#0f0f0f",
        background_color: "#0f0f0f",
        display: "standalone",
        start_url: "/",
        // TODO: add public/icon-192.png + public/icon-512.png
      },
      workbox: {
        // Offline capture: queue failed POSTs and replay them on reconnect.
        runtimeCaching: [
          {
            handler: "NetworkOnly",
            urlPattern: ({ url }) => url.pathname.startsWith("/capture"),
            method: "POST",
            options: {
              backgroundSync: { name: "captureQueue", options: { maxRetentionTime: 24 * 60 } },
            },
          },
        ],
      },
    }),
  ],
  server: { port: 5173 },
});

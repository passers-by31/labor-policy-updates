import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://labor-policy-updates.pages.dev",
  output: "static",
  srcDir: "./src",
  publicDir: "./public",
  vite: {
    plugins: [tailwindcss()],
  },
  integrations: [sitemap()],
});

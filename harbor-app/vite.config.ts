import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

// Local H5: /harbor-api -> local Harbor shop (Chinese titles via hl=zh).
// Fallback production: https://linkiip.com
const SHOP_TARGET = process.env.VITE_SHOP_PROXY || "http://127.0.0.1:8787";

export default defineConfig({
  base: "./",
  plugins: [uni()],
  server: {
    proxy: {
      "/harbor-api": {
        target: SHOP_TARGET,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/harbor-api/, ""),
        cookieDomainRewrite: "",
        cookiePathRewrite: "/",
        ws: true,
      },
    },
  },
});

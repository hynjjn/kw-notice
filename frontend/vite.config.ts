import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// 개발 중에는 /api 를 FastAPI 로 넘겨 같은 origin 처럼 쓴다.
// 배포 시에는 CloudFront 가 같은 일을 한다. 그래서 프론트 코드에 API 주소가 없다.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});

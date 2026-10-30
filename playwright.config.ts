import { defineConfig } from "@playwright/test";

const backend = "http://127.0.0.1:8001";

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: "http://localhost:5174" },
  webServer: [
    {
      command:
        "uv run -m backend.seed && uv run -m uvicorn backend.main:app --port 8001",
      env: { UNDERCOVER_DB: "e2e/e2e.db" },
      url: `${backend}/api/health`,
      reuseExistingServer: false,
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      env: { BACKEND_URL: backend },
      url: "http://localhost:5174",
      reuseExistingServer: false,
    },
  ],
});

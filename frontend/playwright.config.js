import { defineConfig } from "@playwright/test";

const apiBaseUrl = process.env.E2E_API_BASE_URL;
if (!apiBaseUrl) throw new Error("E2E_API_BASE_URL must point to the Cloudflare-backed deployed API.");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.js",
  timeout: 120_000,
  fullyParallel: false,
  reporter: [["list"], ["json", { outputFile: "../artifacts/playwright-results.json" }]],
  use: { baseURL: "http://127.0.0.1:4173", browserName: "chromium", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    env: {
      ...process.env,
      VITE_API_BASE_URL: apiBaseUrl,
      VITE_DEPLOYMENT_CHANNEL: process.env.E2E_DEPLOYMENT_CHANNEL || "production",
    },
  },
});

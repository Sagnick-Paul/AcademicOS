import { defineConfig } from "vitest/config";
import path from "node:path";

// Minimal Vitest config for Phase 4B. Aligned with tsconfig path alias
// (`@/*` → `./src/*`). jsdom is required for DOM globals + RTL.
//
// We do NOT need coverage in CI for Phase 4B. `@vitest/coverage-v8` is
// installed for ad-hoc local runs only — the default `npm test` runs the
// tests, not coverage.
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: false,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});

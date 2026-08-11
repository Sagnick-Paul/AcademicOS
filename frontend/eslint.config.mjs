// Next.js 16 ships eslint-config-next as a native flat config. We import the
// canonical `core-web-vitals` + `typescript` presets directly — no need for
// the legacy FlatCompat shim (which itself crashes on Next 16's configs).
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "next-env.d.ts",
      "out/**",
      "vitest.config.ts",
      "vitest.setup.ts",
      // Vitest test files are validated by the test runner, not ESLint.
      "src/**/*.test.{ts,tsx}",
      "src/**/*.spec.{ts,tsx}",
    ],
  },
];

export default config;

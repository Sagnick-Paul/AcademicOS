// Next.js 16 ships eslint-config-next as a native flat config. We import the
// canonical `core-web-vitals` + `typescript` presets directly — no need for
// the legacy FlatCompat shim (which itself crashes on Next 16's configs).
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "out/**"],
  },
];

export default config;

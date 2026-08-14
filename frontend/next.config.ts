import type { NextConfig } from "next";
import { withReticle } from "@reticlehq/next";

const nextConfig: NextConfig = {
  /**
   * Next.js 16 enables Turbopack by default. `@reticlehq/next` injects a
   * `webpack` config (it predates Turbopack), which makes Next print a
   * "build is using Turbopack, with a webpack config" warning at startup.
   *
   * Adding an empty `turbopack: {}` tells Next we're aware and intentionally
   * using Turbopack. If we ever need custom Turbopack rules (loaders, alias
   * overrides), they go here.
   */
  turbopack: {},
};

export default withReticle(nextConfig);
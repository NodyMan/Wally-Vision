import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = {
  devIndicators: false, // no "N" badge in local screenshots and recordings
  distDir: process.env.NEXT_DIST_DIR || ".next", // lets a test build run next to a running `next dev`
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  outputFileTracingIncludes: {
    "/**": ["./messages/**"],
  },
};

export default withNextIntl(nextConfig);

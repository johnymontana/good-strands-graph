import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.gr-assets.com",
      },
      {
        protocol: "https",
        hostname: "s.gr-assets.com",
      },
      {
        protocol: "https",
        hostname: "i.gr-assets.com",
      },
    ],
  },
};

export default nextConfig;

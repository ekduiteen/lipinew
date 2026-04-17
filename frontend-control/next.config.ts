import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;

if (!backendUrl) {
  throw new Error("Set BACKEND_URL or NEXT_PUBLIC_API_URL for frontend-control.");
}

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

import withPWAInit from "next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: false,
});

/** @type {import('next').NextConfig} */
const allowedOrigins = ["localhost:3000"];
if (process.env.NEXTAUTH_URL) {
  try {
    allowedOrigins.push(new URL(process.env.NEXTAUTH_URL).host);
  } catch {}
}

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    serverActions: { allowedOrigins },
  },
};

export default withPWA(nextConfig);

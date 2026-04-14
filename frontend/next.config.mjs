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

export default nextConfig;

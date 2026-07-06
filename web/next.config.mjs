/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  outputFileTracingRoot: new URL("../", import.meta.url).pathname,
  typedRoutes: false
};

export default nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: new URL("../", import.meta.url).pathname,
  typedRoutes: false
};

export default nextConfig;

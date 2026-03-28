import type { NextConfig } from "next";

const rawBasePath = process.env.NEXT_PUBLIC_BASE_PATH?.trim() ?? "";
const normalizedBasePath =
  rawBasePath && rawBasePath !== "/"
    ? `/${rawBasePath.replace(/^\/+|\/+$/g, "")}`
    : "";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(normalizedBasePath ? { basePath: normalizedBasePath } : {}),
};

export default nextConfig;

const DEFAULT_RENDERER_URL = "http://127.0.0.1:8791";

export function rendererUrl(): string {
  return (process.env.RENDERER_URL || DEFAULT_RENDERER_URL).replace(/\/$/, "");
}

export function rendererRequestUrl(path: string): string {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("renderer path must be an absolute local path");
  }

  const base = new URL(rendererUrl());
  const target = new URL(path, base);
  if (target.origin !== base.origin) {
    throw new Error("renderer path resolved outside the renderer origin");
  }
  return target.toString();
}

export async function proxyRenderer(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (typeof init?.body === "string" && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const rest: RequestInit = { ...(init ?? {}) };
  delete rest.headers;
  const response = await fetch(rendererRequestUrl(path), {
    ...rest,
    headers,
    cache: "no-store"
  });
  return response;
}

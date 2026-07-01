const DEFAULT_RENDERER_URL = "http://127.0.0.1:8791";

export function rendererUrl(): string {
  return (process.env.RENDERER_URL || DEFAULT_RENDERER_URL).replace(/\/$/, "");
}

export async function proxyRenderer(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${rendererUrl()}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "content-type": "application/json" } : {}),
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  return response;
}

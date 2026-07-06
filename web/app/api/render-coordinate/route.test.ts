import { beforeEach, describe, expect, it, vi } from "vitest";
import { proxyRenderer } from "@/lib/renderer";
import { POST } from "./route";

vi.mock("@/lib/renderer", () => ({
  proxyRenderer: vi.fn()
}));

const proxyRendererMock = vi.mocked(proxyRenderer);

describe("/api/render-coordinate", () => {
  beforeEach(() => {
    proxyRendererMock.mockReset();
  });

  it("forwards JSON to the renderer and preserves success metadata", async () => {
    const payload = { imageUrl: "data:image/webp;base64,AAAA", width: 512, height: 512 };
    proxyRendererMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 201,
        statusText: "Created",
        headers: {
          "content-type": "application/json",
          "x-renderer-version": "demo"
        }
      })
    );

    const response = await POST(jsonRequest("/api/render-coordinate", { x: 0, y: 0 }));

    expect(response.status).toBe(201);
    expect(response.statusText).toBe("Created");
    expect(response.headers.get("x-renderer-version")).toBe("demo");
    expect(await response.json()).toEqual(payload);
    const init = proxyRendererMock.mock.calls[0][1] as RequestInit;
    expect(proxyRendererMock.mock.calls[0][0]).toBe("/render-coordinate");
    expect(init.body).toBe(JSON.stringify({ x: 0, y: 0 }));
    expect(new Headers(init.headers).get("content-type")).toBe("application/json");
  });

  it("preserves no-content renderer success responses", async () => {
    proxyRendererMock.mockResolvedValue(new Response(null, { status: 204 }));

    const response = await POST(jsonRequest("/api/render-coordinate", { x: 0, y: 0 }));

    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
  });

  it("sanitizes renderer error bodies", async () => {
    proxyRendererMock.mockResolvedValue(new Response("trace /secret", { status: 502 }));

    const response = await POST(jsonRequest("/api/render-coordinate", { x: 0, y: 0 }));

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ error: "renderer request failed" });
  });
});

function jsonRequest(path: string, body: object): Request {
  return new Request(`http://local.test${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
}

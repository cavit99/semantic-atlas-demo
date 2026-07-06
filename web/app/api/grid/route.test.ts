import { beforeEach, describe, expect, it, vi } from "vitest";
import { proxyRenderer } from "@/lib/renderer";
import { POST } from "./route";

vi.mock("@/lib/renderer", () => ({
  proxyRenderer: vi.fn()
}));

const proxyRendererMock = vi.mocked(proxyRenderer);

describe("/api/grid", () => {
  beforeEach(() => {
    proxyRendererMock.mockReset();
  });

  it("forwards JSON to the renderer and preserves success status", async () => {
    proxyRendererMock.mockResolvedValue(
      new Response(JSON.stringify({ jobId: "job-1", backend: "mock-live" }), {
        status: 202,
        statusText: "Accepted",
        headers: {
          "content-type": "application/json",
          "connection": "x-internal-hop",
          "x-internal-hop": "drop-me",
          "x-renderer-version": "demo"
        }
      })
    );

    const response = await POST(jsonRequest("/api/grid", { ideaId: "x" }));

    expect(response.status).toBe(202);
    expect(response.statusText).toBe("Accepted");
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(response.headers.get("x-renderer-version")).toBe("demo");
    expect(response.headers.get("connection")).toBeNull();
    expect(response.headers.get("x-internal-hop")).toBeNull();
    expect(await response.json()).toEqual({ jobId: "job-1", backend: "mock-live" });
    expect(proxyRendererMock).toHaveBeenCalledWith(
      "/grid",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ ideaId: "x" })
      })
    );
    const headers = new Headers(proxyRendererMock.mock.calls[0][1]?.headers);
    expect(headers.get("content-type")).toBe("application/json");
  });

  it("preserves no-content renderer success responses", async () => {
    proxyRendererMock.mockResolvedValue(
      new Response(null, {
        status: 204,
        statusText: "No Content",
        headers: { "x-renderer-version": "demo" }
      })
    );

    const response = await POST(jsonRequest("/api/grid", { ideaId: "x" }));

    expect(response.status).toBe(204);
    expect(response.statusText).toBe("No Content");
    expect(response.headers.get("x-renderer-version")).toBe("demo");
    expect(await response.text()).toBe("");
  });

  it("rejects unsupported content types and oversized bodies before proxying", async () => {
    const badType = await POST(
      new Request("http://local.test/api/grid", {
        method: "POST",
        headers: { "content-type": "text/plain" },
        body: "{}"
      })
    );
    expect(badType.status).toBe(415);

    const oversized = await POST(
      new Request("http://local.test/api/grid", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ value: "x".repeat(20_000) })
      })
    );
    expect(oversized.status).toBe(413);
    expect(proxyRendererMock).not.toHaveBeenCalled();
  });

  it("sanitizes renderer errors and handles renderer outages", async () => {
    proxyRendererMock.mockResolvedValueOnce(
      new Response("stack trace /private/path", { status: 500 })
    );

    const failed = await POST(jsonRequest("/api/grid", { ideaId: "x" }));
    expect(failed.status).toBe(500);
    expect(await failed.json()).toEqual({ error: "renderer request failed" });

    proxyRendererMock.mockRejectedValueOnce(new Error("ECONNREFUSED"));
    const unavailable = await POST(jsonRequest("/api/grid", { ideaId: "x" }));
    expect(unavailable.status).toBe(503);
    expect(await unavailable.json()).toEqual({ error: "renderer unavailable" });
  });
});

function jsonRequest(path: string, body: object): Request {
  return new Request(`http://local.test${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
}

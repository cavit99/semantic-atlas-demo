import { beforeEach, describe, expect, it, vi } from "vitest";
import { proxyRenderer } from "@/lib/renderer";
import { GET } from "./route";

vi.mock("@/lib/renderer", () => ({
  proxyRenderer: vi.fn()
}));

const proxyRendererMock = vi.mocked(proxyRenderer);

describe("/api/grid/[jobId]/events", () => {
  beforeEach(() => {
    proxyRendererMock.mockReset();
  });

  it("returns SSE without hop-by-hop connection headers", async () => {
    proxyRendererMock.mockResolvedValue(
      new Response("data: {}\n\n", {
        status: 200,
        statusText: "OK",
        headers: {
          "content-type": "text/event-stream",
          "connection": "x-internal-hop",
          "x-internal-hop": "drop-me",
          "x-renderer-stream": "1"
        }
      })
    );

    const response = await GET(new Request("http://local.test/api/grid/job-1/events"), {
      params: Promise.resolve({ jobId: "job-1" })
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("text/event-stream; charset=utf-8");
    expect(response.headers.get("cache-control")).toBe("no-cache, no-transform");
    expect(response.headers.get("connection")).toBeNull();
    expect(response.headers.get("x-internal-hop")).toBeNull();
    expect(response.headers.get("x-renderer-stream")).toBe("1");
    expect(proxyRendererMock).toHaveBeenCalledWith("/grid/job-1/events", {
      method: "GET",
      headers: { accept: "text/event-stream" }
    });
  });

  it("handles renderer outage with a controlled 503", async () => {
    proxyRendererMock.mockRejectedValue(new Error("ECONNREFUSED"));

    const response = await GET(new Request("http://local.test/api/grid/job-1/events"), {
      params: Promise.resolve({ jobId: "job-1" })
    });

    expect(response.status).toBe(503);
    expect(await response.text()).toBe("renderer unavailable");
  });
});

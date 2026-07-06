import { afterEach, describe, expect, it, vi } from "vitest";
import { proxyRenderer, rendererRequestUrl } from "./renderer";

describe("renderer proxy URL handling", () => {
  afterEach(() => {
    delete process.env.RENDERER_URL;
    vi.unstubAllGlobals();
  });

  it("builds renderer-local URLs only", () => {
    expect(rendererRequestUrl("/grid")).toBe("http://127.0.0.1:8791/grid");
    expect(() => rendererRequestUrl("@attacker.test/render")).toThrow(
      "renderer path must be an absolute local path"
    );
    expect(() => rendererRequestUrl("//attacker.test/render")).toThrow(
      "renderer path must be an absolute local path"
    );
  });

  it("normalizes RequestInit headers and defaults JSON for string bodies", async () => {
    const fetchCalls: Array<[RequestInfo | URL, RequestInit?]> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      fetchCalls.push([input, init]);
      return new Response("ok");
    });
    vi.stubGlobal("fetch", fetchMock);

    await proxyRenderer("/grid", {
      method: "POST",
      body: "{}",
      headers: new Headers([["authorization", "Bearer token"]])
    });

    const init = fetchCalls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(fetchCalls[0][0]).toBe("http://127.0.0.1:8791/grid");
    expect(headers.get("authorization")).toBe("Bearer token");
    expect(headers.get("content-type")).toBe("application/json");
  });

  it("does not force JSON content type for non-string bodies", async () => {
    const fetchCalls: Array<[RequestInfo | URL, RequestInit?]> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      fetchCalls.push([input, init]);
      return new Response("ok");
    });
    vi.stubGlobal("fetch", fetchMock);

    await proxyRenderer("/grid", {
      method: "POST",
      body: new URLSearchParams([["x", "1"]])
    });

    const init = fetchCalls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.has("content-type")).toBe(false);
  });
});

import { rendererResponseHeaders } from "@/lib/route-helpers";
import { proxyRenderer } from "@/lib/renderer";

type Props = {
  params: Promise<{ jobId: string }>;
};

export async function GET(_request: Request, { params }: Props) {
  const { jobId } = await params;
  let response: Response;
  try {
    response = await proxyRenderer(`/grid/${encodeURIComponent(jobId)}/events`, {
      method: "GET",
      headers: { accept: "text/event-stream" }
    });
  } catch {
    return new Response("renderer unavailable", { status: 503 });
  }

  if (!response.ok || !response.body) {
    const status = response.ok ? 502 : response.status;
    await response.text().catch(() => "");
    return new Response("renderer stream unavailable", { status });
  }

  const headers = rendererResponseHeaders(response.headers);
  headers.set("content-type", "text/event-stream; charset=utf-8");
  headers.set("cache-control", "no-cache, no-transform");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

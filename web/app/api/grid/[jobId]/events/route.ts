import { proxyRenderer } from "@/lib/renderer";

type Props = {
  params: Promise<{ jobId: string }>;
};

export async function GET(_request: Request, { params }: Props) {
  const { jobId } = await params;
  const response = await proxyRenderer(`/grid/${encodeURIComponent(jobId)}/events`, {
    method: "GET",
    headers: { accept: "text/event-stream" }
  });

  if (!response.ok || !response.body) {
    return new Response(await response.text(), { status: response.status });
  }

  return new Response(response.body, {
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive"
    }
  });
}

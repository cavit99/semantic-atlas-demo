import {
  readJsonRequestBody,
  rendererFailureResponse,
  rendererResponseHeaders,
  rendererUnavailableResponse
} from "@/lib/route-helpers";
import { proxyRenderer } from "@/lib/renderer";

export async function POST(request: Request) {
  const body = await readJsonRequestBody(request);
  if (!body.ok) {
    return body.response;
  }

  let response: Response;
  try {
    response = await proxyRenderer("/render-coordinate", {
      method: "POST",
      body: body.body,
      headers: body.headers
    });
  } catch {
    return rendererUnavailableResponse("render-coordinate");
  }

  if (!response.ok) {
    return rendererFailureResponse(response, "render-coordinate");
  }

  return new Response(response.status === 204 || response.status === 205 ? null : response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: rendererResponseHeaders(response.headers)
  });
}

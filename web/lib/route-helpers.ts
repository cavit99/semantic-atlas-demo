import { NextResponse } from "next/server";

const MAX_JSON_BODY_BYTES = 16 * 1024;

type JsonBodyResult =
  | {
      ok: true;
      body: string;
      headers: Headers;
    }
  | {
      ok: false;
      response: NextResponse;
    };

export async function readJsonRequestBody(
  request: Request,
  maxBytes = MAX_JSON_BODY_BYTES
): Promise<JsonBodyResult> {
  const mediaType = request.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase();
  if (mediaType !== "application/json") {
    return {
      ok: false,
      response: NextResponse.json({ error: "expected application/json" }, { status: 415 })
    };
  }

  const contentLength = request.headers.get("content-length");
  if (contentLength) {
    const parsedLength = Number(contentLength);
    if (!Number.isFinite(parsedLength) || parsedLength < 0) {
      return {
        ok: false,
        response: NextResponse.json({ error: "invalid content-length" }, { status: 400 })
      };
    }
    if (parsedLength > maxBytes) {
      return {
        ok: false,
        response: NextResponse.json({ error: "request body too large" }, { status: 413 })
      };
    }
  }

  const body = await readTextWithLimit(request.body, maxBytes);
  if (body.tooLarge) {
    return {
      ok: false,
      response: NextResponse.json({ error: "request body too large" }, { status: 413 })
    };
  }

  try {
    JSON.parse(body.text);
  } catch {
    return {
      ok: false,
      response: NextResponse.json({ error: "invalid json" }, { status: 400 })
    };
  }

  return {
    ok: true,
    body: body.text,
    headers: new Headers({ "content-type": "application/json" })
  };
}

export async function rendererFailureResponse(
  response: Response,
  operation: string
): Promise<NextResponse> {
  const detail = await response.text().catch(() => "");
  if (detail) {
    console.error(`renderer ${operation} failed`, {
      status: response.status,
      detail: detail.slice(0, 1000)
    });
  }
  return NextResponse.json({ error: "renderer request failed" }, { status: response.status });
}

export function rendererUnavailableResponse(operation: string): NextResponse {
  console.error(`renderer ${operation} unavailable`);
  return NextResponse.json({ error: "renderer unavailable" }, { status: 503 });
}

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);

export function rendererResponseHeaders(headers: Headers): Headers {
  const blocked = new Set(HOP_BY_HOP_HEADERS);
  const connectionHeader = headers.get("connection");
  if (connectionHeader) {
    for (const header of connectionHeader.split(",")) {
      blocked.add(header.trim().toLowerCase());
    }
  }

  const forwarded = new Headers();
  headers.forEach((value, key) => {
    if (!blocked.has(key.toLowerCase())) {
      forwarded.set(key, value);
    }
  });
  return forwarded;
}

async function readTextWithLimit(
  body: ReadableStream<Uint8Array> | null,
  maxBytes: number
): Promise<{ tooLarge: true } | { tooLarge: false; text: string }> {
  if (!body) {
    return { tooLarge: false, text: "" };
  }

  const reader = body.getReader();
  const decoder = new TextDecoder();
  let totalBytes = 0;
  let text = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    totalBytes += value.byteLength;
    if (totalBytes > maxBytes) {
      await reader.cancel();
      return { tooLarge: true };
    }
    text += decoder.decode(value, { stream: true });
  }

  text += decoder.decode();
  return { tooLarge: false, text };
}

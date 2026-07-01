import { NextResponse } from "next/server";
import { proxyRenderer } from "@/lib/renderer";

export async function POST(request: Request) {
  const body = await request.text();
  const response = await proxyRenderer("/render-coordinate", {
    method: "POST",
    body
  });

  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json(
      { error: `renderer failed: ${response.status} ${detail}` },
      { status: response.status }
    );
  }

  return NextResponse.json(await response.json());
}

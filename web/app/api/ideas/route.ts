import { NextResponse } from "next/server";
import { loadIdeas } from "@/lib/ideas";

export async function GET() {
  return NextResponse.json({ ideas: await loadIdeas() });
}

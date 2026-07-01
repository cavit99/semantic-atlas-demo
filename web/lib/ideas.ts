import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { DemoIdea } from "./types";

const ideasPath = join(process.cwd(), "..", "data", "ideas.json");

export async function loadIdeas(): Promise<DemoIdea[]> {
  const raw = await readFile(ideasPath, "utf8");
  return JSON.parse(raw) as DemoIdea[];
}

export async function loadIdea(id: string): Promise<DemoIdea | undefined> {
  return (await loadIdeas()).find((idea) => idea.id === id);
}

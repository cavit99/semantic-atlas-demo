import { beforeEach, describe, expect, it, vi } from "vitest";
import { isValidElement, type ReactElement } from "react";
import { loadIdea } from "@/lib/ideas";
import { notFound } from "next/navigation";
import { LiveGrid } from "@/components/LiveGrid";
import type { DemoIdea } from "@/lib/types";
import AtlasPage from "./page";

vi.mock("@/components/LiveGrid", () => ({
  LiveGrid: vi.fn(() => null)
}));

vi.mock("@/lib/ideas", () => ({
  loadIdea: vi.fn()
}));

vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  })
}));

const loadIdeaMock = vi.mocked(loadIdea);
const liveGridMock = vi.mocked(LiveGrid);
const notFoundMock = vi.mocked(notFound);

describe("/atlas/[ideaId]", () => {
  beforeEach(() => {
    loadIdeaMock.mockReset();
    liveGridMock.mockClear();
    notFoundMock.mockClear();
  });

  it("loads the selected idea and passes it to the grid", async () => {
    loadIdeaMock.mockResolvedValue(demoIdea);

    const page = await AtlasPage({ params: Promise.resolve({ ideaId: "demo" }) });

    expect(loadIdeaMock).toHaveBeenCalledWith("demo");
    expect(isValidElement(page)).toBe(true);
    const children = page.props.children as ReactElement[];
    const grid = children.at(-1) as ReactElement<{ idea: DemoIdea }>;
    expect(grid.type).toBe(liveGridMock);
    expect(grid.props.idea).toBe(demoIdea);
  });

  it("uses the not found route for unknown ideas", async () => {
    loadIdeaMock.mockResolvedValue(undefined);

    await expect(AtlasPage({ params: Promise.resolve({ ideaId: "missing" }) })).rejects.toThrow(
      "NEXT_NOT_FOUND"
    );
    expect(notFoundMock).toHaveBeenCalled();
  });
});

const demoIdea: DemoIdea = {
  id: "demo",
  title: "Demo",
  family: "test",
  scene: "Test scene",
  midpointPrompt: "Test midpoint",
  xAxis: {
    negativeLabel: "left",
    positiveLabel: "right",
    negativePrompt: "left prompt",
    positivePrompt: "right prompt"
  },
  yAxis: {
    negativeLabel: "down",
    positiveLabel: "up",
    negativePrompt: "down prompt",
    positivePrompt: "up prompt"
  },
  palette: ["#000000", "#111111", "#222222", "#333333"],
  suffix: "test suffix"
};

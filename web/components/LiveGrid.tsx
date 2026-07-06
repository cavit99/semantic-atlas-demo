"use client";

/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import type { CSSProperties, KeyboardEvent, PointerEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Axis, DemoIdea, GridCellEvent, GridEvent } from "@/lib/types";

type Props = {
  idea: DemoIdea;
};

type Cell = GridCellEvent;
type BatchSize = 1 | 3 | 9 | 25;
type Coord = { index: number; row: number; col: number; x: number; y: number };
const MAX_SEED = 4_294_967_295;
const GRID_SIZE = 5;
const TOTAL_CELLS = GRID_SIZE * GRID_SIZE;
const CENTER_INDEX = Math.floor(TOTAL_CELLS / 2);
const BATCH_SIZES = [1, 3, 9, 25] as const;

const coords = Array.from({ length: TOTAL_CELLS }, (_, index): Coord => {
  const row = Math.floor(index / GRID_SIZE);
  const col = index % GRID_SIZE;
  return {
    index,
    row,
    col,
    x: -1 + (2 * col) / (GRID_SIZE - 1),
    y: 1 - (2 * row) / (GRID_SIZE - 1)
  };
});

export function LiveGrid({ idea }: Props) {
  const [cells, setCells] = useState<Record<number, Cell>>({});
  const [status, setStatus] = useState<"idle" | "starting" | "running" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [backend, setBackend] = useState<string>("waiting");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);
  const [liveElapsedMs, setLiveElapsedMs] = useState(0);
  const [activeBatchSize, setActiveBatchSize] = useState(0);
  const [activeIndices, setActiveIndices] = useState<number[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(CENTER_INDEX);
  const [progressText, setProgressText] = useState("Ready to generate.");
  const eventSource = useRef<EventSource | null>(null);
  const defaultSeed = useMemo(() => stableSeed(idea.id), [idea.id]);
  const [seedInput, setSeedInput] = useState(() => String(defaultSeed));
  const [batchSize, setBatchSize] = useState<BatchSize>(25);
  const [xAxis, setXAxis] = useState<Axis>(() => ({ ...idea.xAxis }));
  const [yAxis, setYAxis] = useState<Axis>(() => ({ ...idea.yAxis }));

  const completed = Object.keys(cells).length;
  const visibleElapsedMs = status === "running" || status === "starting" ? liveElapsedMs : elapsedMs;
  const selectedCoord = coords[selectedIndex];
  const selectedCell = cells[selectedIndex];
  const centerCell = cells[CENTER_INDEX];
  const displayCell = selectedCell ?? centerCell;
  const progressPercent = Math.round((completed / TOTAL_CELLS) * 100);
  const seedLocked = status === "starting" || status === "running";

  const selectedPointStyle = {
    "--atlas-x": selectedCoord.col / (GRID_SIZE - 1),
    "--atlas-y": selectedCoord.row / (GRID_SIZE - 1)
  } as CSSProperties;

  const startGrid = useCallback(async () => {
    const worldSeed = parseSeed(seedInput);
    if (worldSeed === null) {
      setStatus("error");
      setError(`Seed must be a whole number from 0 to ${MAX_SEED}.`);
      setProgressText("Seed needs a valid number.");
      return;
    }
    const nextXAxis = normalizeAxis(xAxis);
    const nextYAxis = normalizeAxis(yAxis);
    if (!nextXAxis || !nextYAxis) {
      setStatus("error");
      setError("Axis labels and prompts must all be filled in.");
      setProgressText("Axes need complete labels and prompts.");
      return;
    }

    eventSource.current?.close();
    setCells({});
    setStatus("starting");
    setError(null);
    setBackend("starting");
    setElapsedMs(0);
    setLiveElapsedMs(0);
    setActiveBatchSize(0);
    setActiveIndices([]);
    setSelectedIndex(CENTER_INDEX);
    setProgressText("Starting renderer job.");
    setRunStartedAt(Date.now());

    try {
      const response = await fetch("/api/grid", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ideaId: idea.id,
          gridSize: GRID_SIZE,
          worldSeed,
          batchSize,
          xAxis: nextXAxis,
          yAxis: nextYAxis,
          width: 512,
          height: 512
        })
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as {
        jobId: string;
        backend: string;
        initialBatchSize: number;
        initialIndices: number[];
      };
      setBackend(payload.backend);
      setStatus("running");
      setActiveBatchSize(payload.initialBatchSize);
      setActiveIndices(payload.initialIndices);
      setProgressText(
        payload.initialBatchSize >= TOTAL_CELLS
          ? "Rendering the full atlas in one Flux batch."
          : `Rendering first ${payload.initialBatchSize} cell${payload.initialBatchSize === 1 ? "" : "s"}.`
      );

      const source = new EventSource(`/api/grid/${payload.jobId}/events`);
      eventSource.current = source;
      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as GridEvent;
        if (event.type === "cell") {
          setCells((current) => ({ ...current, [event.index]: event }));
          setActiveIndices((current) => current.filter((index) => index !== event.index));
          setBackend(event.backend);
          setElapsedMs(event.elapsedMs);
          setProgressText("Receiving rendered cells.");
        } else if (event.type === "progress") {
          setBackend(event.backend);
          setElapsedMs(event.elapsedMs);
          setActiveBatchSize(event.batchSize);
          setActiveIndices(event.indices);
          setProgressText(
            event.batchSize >= TOTAL_CELLS
              ? "Rendering the full atlas in one Flux batch."
              : `Rendering next ${event.batchSize} cell${event.batchSize === 1 ? "" : "s"}.`
          );
        } else if (event.type === "done") {
          setStatus("done");
          setBackend(event.backend);
          setElapsedMs(event.elapsedMs);
          setLiveElapsedMs(event.elapsedMs);
          setActiveBatchSize(0);
          setActiveIndices([]);
          setProgressText("Grid complete.");
          source.close();
        } else if (event.type === "error") {
          setStatus("error");
          setError(event.message);
          setActiveBatchSize(0);
          setActiveIndices([]);
          setProgressText("Generation failed.");
          source.close();
        }
      };
      source.onerror = () => {
        setStatus("error");
        setError("Lost connection to the renderer event stream.");
        setActiveBatchSize(0);
        setActiveIndices([]);
        setProgressText("Connection lost.");
        source.close();
      };
    } catch (caught) {
      setStatus("error");
      setError(caught instanceof Error ? caught.message : "Grid generation failed.");
      setActiveBatchSize(0);
      setActiveIndices([]);
      setProgressText("Generation failed.");
    }
  }, [batchSize, idea.id, seedInput, xAxis, yAxis]);

  useEffect(() => {
    setSeedInput(String(defaultSeed));
    setXAxis({ ...idea.xAxis });
    setYAxis({ ...idea.yAxis });
  }, [defaultSeed, idea.xAxis, idea.yAxis]);

  useEffect(() => {
    return () => eventSource.current?.close();
  }, []);

  useEffect(() => {
    if (!runStartedAt || (status !== "starting" && status !== "running")) {
      return;
    }
    const timer = window.setInterval(() => {
      setLiveElapsedMs(Date.now() - runStartedAt);
    }, 250);
    return () => window.clearInterval(timer);
  }, [runStartedAt, status]);

  const selectFromPointer = useCallback((event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = clamp((event.clientX - bounds.left) / bounds.width, 0, 1);
    const y = clamp((event.clientY - bounds.top) / bounds.height, 0, 1);
    const col = Math.round(x * (GRID_SIZE - 1));
    const row = Math.round(y * (GRID_SIZE - 1));
    setSelectedIndex(row * GRID_SIZE + col);
  }, []);

  const handleStagePointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      selectFromPointer(event);
    },
    [selectFromPointer]
  );

  const moveSelection = useCallback((deltaCol: number, deltaRow: number) => {
    setSelectedIndex((current) => {
      const currentCoord = coords[current];
      const nextCol = clamp(currentCoord.col + deltaCol, 0, GRID_SIZE - 1);
      const nextRow = clamp(currentCoord.row + deltaRow, 0, GRID_SIZE - 1);
      return nextRow * GRID_SIZE + nextCol;
    });
  }, []);

  const handleStageKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
        event.preventDefault();
        moveSelection(-1, 0);
      } else if (event.key === "ArrowRight" || event.key.toLowerCase() === "d") {
        event.preventDefault();
        moveSelection(1, 0);
      } else if (event.key === "ArrowUp" || event.key.toLowerCase() === "w") {
        event.preventDefault();
        moveSelection(0, -1);
      } else if (event.key === "ArrowDown" || event.key.toLowerCase() === "s") {
        event.preventDefault();
        moveSelection(0, 1);
      } else if (event.key === "Home") {
        event.preventDefault();
        setSelectedIndex(CENTER_INDEX);
      }
    },
    [moveSelection]
  );

  return (
    <section className="gridStage">
      <aside className="atlasPanel" style={paletteStyle(idea.palette)}>
        <div className="ideaMeta">
          <span className="tileFamily">{idea.family}</span>
          <h1>{idea.title}</h1>
          <p>{idea.scene}</p>
        </div>

        <div className="runStats">
          <div>
            <span>Cells</span>
            <strong>
              {completed}/{TOTAL_CELLS}
            </strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>{backend}</strong>
          </div>
          <div>
            <span>Elapsed</span>
            <strong>{formatMs(visibleElapsedMs)}</strong>
          </div>
        </div>

        <div className="generationControls">
          <div className="seedControl">
            <label htmlFor="seed-input">
              <span>Seed</span>
              <input
                id="seed-input"
                inputMode="numeric"
                max={MAX_SEED}
                min={0}
                onChange={(event) => setSeedInput(event.target.value)}
                pattern="[0-9]*"
                type="number"
                value={seedInput}
                disabled={seedLocked}
              />
            </label>
            <button disabled={seedLocked} onClick={() => setSeedInput(String(defaultSeed))} type="button">
              Default
            </button>
          </div>

          <fieldset className="batchControl" disabled={seedLocked}>
            <legend>Batch</legend>
            <div className="batchOptions">
              {BATCH_SIZES.map((size) => (
                <button
                  aria-pressed={batchSize === size}
                  className={batchSize === size ? "selected" : undefined}
                  key={size}
                  onClick={() => setBatchSize(size)}
                  type="button"
                >
                  {size}
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        <details className="axisEditor">
          <summary>
            <span className="axisEditorTitle">Axes</span>
            <div className="axisSummaryGrid">
              <div>
                <span>X</span>
                <strong>
                  {xAxis.negativeLabel} / {xAxis.positiveLabel}
                </strong>
              </div>
              <div>
                <span>Y</span>
                <strong>
                  {yAxis.negativeLabel} / {yAxis.positiveLabel}
                </strong>
              </div>
            </div>
          </summary>
          <div className="axisEditorBody">
            <AxisEditor
              axis={xAxis}
              disabled={seedLocked}
              label="X axis"
              negativeSide="Left"
              onChange={setXAxis}
              positiveSide="Right"
            />
            <AxisEditor
              axis={yAxis}
              disabled={seedLocked}
              label="Y axis"
              negativeSide="Bottom"
              onChange={setYAxis}
              positiveSide="Top"
            />
            <button
              className="resetAxesButton"
              disabled={seedLocked}
              onClick={() => {
                setXAxis({ ...idea.xAxis });
                setYAxis({ ...idea.yAxis });
              }}
              type="button"
            >
              Reset axes
            </button>
          </div>
        </details>

        <div className="progressBlock">
          <div className="progressMeta">
            <span>{statusLabel(status)}</span>
            <strong>{progressPercent}%</strong>
          </div>
          <div className="progressTrack" aria-label="Generation progress">
            <span style={{ width: `${progressPercent}%` }} />
          </div>
          <p>{activeBatchSize > 0 ? `${progressText} Batch size ${activeBatchSize}.` : progressText}</p>
        </div>

        <div className="panelActions">
          <button className="primaryButton" onClick={startGrid} type="button">
            {buttonLabel(status)}
          </button>
          <Link href="/" className="secondaryButton">
            Change idea
          </Link>
        </div>

        {error ? <p className="errorText">{error}</p> : null}
      </aside>

      <div className="atlasExplorer" style={paletteStyle(idea.palette)}>
        <div className="atlasViewport">
          <div className="atlasCanvasShell">
            <div className="axisLabel top">{yAxis.positiveLabel}</div>
            <div className="axisLabel bottom">{yAxis.negativeLabel}</div>
            <div className="axisLabel left">{xAxis.negativeLabel}</div>
            <div className="axisLabel right">{xAxis.positiveLabel}</div>

            <div
              aria-label={`${idea.title} semantic atlas canvas`}
              className="atlasImageStage"
              onKeyDown={handleStageKeyDown}
              onPointerDown={handleStagePointerDown}
              onPointerMove={selectFromPointer}
              role="application"
              tabIndex={0}
            >
              {displayCell ? (
                <img
                  src={displayCell.imageUrl}
                  alt={`${idea.title} x ${formatCoord(displayCell.x)} y ${formatCoord(displayCell.y)}`}
                />
              ) : (
                <img src={`/previews/${idea.id}.webp`} alt={`${idea.title} center preview`} />
              )}
              <span className="atlasStageCursor" style={selectedPointStyle} />
            </div>
          </div>

          <div className="atlasMapShell">
            <div className="atlasMapMeta">
              <span>Map</span>
              <strong>
                {selectedCoord.col + 1},{selectedCoord.row + 1}
              </strong>
            </div>
            <div
              aria-label={`${idea.title} semantic atlas map`}
              className="atlasMap"
              onPointerDown={selectFromPointer}
              onPointerMove={selectFromPointer}
            >
              <span
                className="atlasCrosshair"
                style={
                  {
                    "--atlas-col": selectedCoord.col,
                    "--atlas-row": selectedCoord.row
                  } as CSSProperties
                }
              />
              {coords.map((coord) => {
                const cell = cells[coord.index];
                const isGenerating = activeIndices.includes(coord.index);
                const isSelected = coord.index === selectedIndex;
                return (
                  <button
                    aria-label={`Select x ${formatCoord(coord.x)} y ${formatCoord(coord.y)}`}
                    aria-pressed={isSelected}
                    className={[
                      "atlasTile",
                      cell ? "ready" : isGenerating ? "generating" : "queued",
                      isSelected ? "selected" : ""
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    key={coord.index}
                    onFocus={() => setSelectedIndex(coord.index)}
                    onPointerEnter={() => setSelectedIndex(coord.index)}
                    type="button"
                  >
                    {cell ? <img src={cell.imageUrl} alt="" /> : <span />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

type AxisEditorProps = {
  axis: Axis;
  disabled: boolean;
  label: string;
  negativeSide: string;
  onChange: (axis: Axis) => void;
  positiveSide: string;
};

function AxisEditor({ axis, disabled, label, negativeSide, onChange, positiveSide }: AxisEditorProps) {
  const update = (field: keyof Axis, value: string) => {
    onChange({ ...axis, [field]: value });
  };

  return (
    <fieldset className="axisFieldset" disabled={disabled}>
      <legend>{label}</legend>
      <div className="axisLabelPair">
        <label>
          <span>{negativeSide}</span>
          <input value={axis.negativeLabel} onChange={(event) => update("negativeLabel", event.target.value)} />
        </label>
        <label>
          <span>{positiveSide}</span>
          <input value={axis.positiveLabel} onChange={(event) => update("positiveLabel", event.target.value)} />
        </label>
      </div>
      <label>
        <span>Negative prompt</span>
        <textarea
          rows={2}
          value={axis.negativePrompt}
          onChange={(event) => update("negativePrompt", event.target.value)}
        />
      </label>
      <label>
        <span>Positive prompt</span>
        <textarea
          rows={2}
          value={axis.positivePrompt}
          onChange={(event) => update("positivePrompt", event.target.value)}
        />
      </label>
    </fieldset>
  );
}

function stableSeed(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % 1_000_000_000;
}

function parseSeed(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isSafeInteger(parsed) || parsed < 0 || parsed > MAX_SEED) {
    return null;
  }
  return parsed;
}

function normalizeAxis(axis: Axis): Axis | null {
  const normalized = {
    negativeLabel: axis.negativeLabel.trim(),
    positiveLabel: axis.positiveLabel.trim(),
    negativePrompt: axis.negativePrompt.trim(),
    positivePrompt: axis.positivePrompt.trim()
  };
  return Object.values(normalized).every(Boolean) ? normalized : null;
}

function formatMs(value: number): string {
  if (!value) {
    return "0.0s";
  }
  return `${(value / 1000).toFixed(1)}s`;
}

function formatCoord(value: number): string {
  if (Object.is(value, -0) || Math.abs(value) < 0.001) {
    return "0";
  }
  return `${value > 0 ? "+" : ""}${Number(value.toFixed(2))}`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function statusLabel(status: "idle" | "starting" | "running" | "done" | "error"): string {
  if (status === "starting") {
    return "Starting";
  }
  if (status === "running") {
    return "Generating";
  }
  if (status === "done") {
    return "Complete";
  }
  if (status === "error") {
    return "Error";
  }
  return "Idle";
}

function buttonLabel(status: "idle" | "starting" | "running" | "done" | "error"): string {
  if (status === "idle") {
    return "Generate 5x5 atlas";
  }
  if (status === "starting" || status === "running") {
    return "Restart";
  }
  return "Generate again";
}

function paletteStyle(palette: string[]): CSSProperties {
  return {
    "--p0": palette[0],
    "--p1": palette[1],
    "--p2": palette[2],
    "--p3": palette[3]
  } as CSSProperties;
}

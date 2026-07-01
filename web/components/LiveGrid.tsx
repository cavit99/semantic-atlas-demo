"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DemoIdea, GridCellEvent, GridEvent } from "@/lib/types";

type Props = {
  idea: DemoIdea;
};

type Cell = GridCellEvent;

const coords = [
  { index: 0, row: 0, col: 0, x: -1, y: 1 },
  { index: 1, row: 0, col: 1, x: 0, y: 1 },
  { index: 2, row: 0, col: 2, x: 1, y: 1 },
  { index: 3, row: 1, col: 0, x: -1, y: 0 },
  { index: 4, row: 1, col: 1, x: 0, y: 0 },
  { index: 5, row: 1, col: 2, x: 1, y: 0 },
  { index: 6, row: 2, col: 0, x: -1, y: -1 },
  { index: 7, row: 2, col: 1, x: 0, y: -1 },
  { index: 8, row: 2, col: 2, x: 1, y: -1 }
];

export function LiveGrid({ idea }: Props) {
  const [cells, setCells] = useState<Record<number, Cell>>({});
  const [status, setStatus] = useState<"idle" | "starting" | "running" | "done" | "error">("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backend, setBackend] = useState<string>("waiting");
  const [elapsedMs, setElapsedMs] = useState(0);
  const started = useRef(false);
  const eventSource = useRef<EventSource | null>(null);
  const worldSeed = useMemo(() => stableSeed(idea.id), [idea.id]);

  const completed = Object.keys(cells).length;

  const startGrid = useCallback(async () => {
    eventSource.current?.close();
    started.current = true;
    setCells({});
    setStatus("starting");
    setError(null);
    setJobId(null);
    setBackend("starting");
    setElapsedMs(0);

    try {
      const response = await fetch("/api/grid", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          ideaId: idea.id,
          gridSize: 3,
          worldSeed,
          width: 512,
          height: 512
        })
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as { jobId: string; backend: string };
      setJobId(payload.jobId);
      setBackend(payload.backend);
      setStatus("running");

      const source = new EventSource(`/api/grid/${payload.jobId}/events`);
      eventSource.current = source;
      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as GridEvent;
        if (event.type === "cell") {
          setCells((current) => ({ ...current, [event.index]: event }));
          setBackend(event.backend);
          setElapsedMs(event.elapsedMs);
        } else if (event.type === "done") {
          setStatus("done");
          setBackend(event.backend);
          setElapsedMs(event.elapsedMs);
          source.close();
        } else if (event.type === "error") {
          setStatus("error");
          setError(event.message);
          source.close();
        }
      };
      source.onerror = () => {
        setStatus("error");
        setError("Lost connection to the renderer event stream.");
        source.close();
      };
    } catch (caught) {
      setStatus("error");
      setError(caught instanceof Error ? caught.message : "Grid generation failed.");
    }
  }, [idea.id, worldSeed]);

  useEffect(() => {
    if (!started.current) {
      void startGrid();
    }
    return () => eventSource.current?.close();
  }, [startGrid]);

  return (
    <section className="gridStage">
      <aside className="atlasPanel" style={paletteStyle(idea.palette)}>
        <div className="ideaMeta">
          <span className="tileFamily">{idea.family}</span>
          <h1>{idea.title}</h1>
          <p>{idea.scene}</p>
        </div>

        <div className="axisReadout">
          <div>
            <span>X axis</span>
            <strong>
              {idea.xAxis.negativeLabel} / {idea.xAxis.positiveLabel}
            </strong>
          </div>
          <div>
            <span>Y axis</span>
            <strong>
              {idea.yAxis.negativeLabel} / {idea.yAxis.positiveLabel}
            </strong>
          </div>
        </div>

        <div className="runStats">
          <div>
            <span>Cells</span>
            <strong>{completed}/9</strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>{backend}</strong>
          </div>
          <div>
            <span>Elapsed</span>
            <strong>{formatMs(elapsedMs)}</strong>
          </div>
        </div>

        <div className="panelActions">
          <button className="primaryButton" onClick={startGrid} type="button">
            {status === "running" || status === "starting" ? "Restart" : "Generate again"}
          </button>
          <Link href="/" className="secondaryButton">
            Change idea
          </Link>
        </div>

        {error ? <p className="errorText">{error}</p> : null}
      </aside>

      <div className="gridWrap" style={paletteStyle(idea.palette)}>
        <div className="axisLabel top">{idea.yAxis.positiveLabel}</div>
        <div className="axisLabel bottom">{idea.yAxis.negativeLabel}</div>
        <div className="axisLabel left">{idea.xAxis.negativeLabel}</div>
        <div className="axisLabel right">{idea.xAxis.positiveLabel}</div>

        <div className="imageGrid" aria-label={`${idea.title} live 3 by 3 grid`}>
          {coords.map((coord) => {
            const cell = cells[coord.index];
            return (
              <figure
                key={coord.index}
                className={cell ? "gridCell ready" : "gridCell pending"}
                style={{ "--cell-order": coord.index } as CSSProperties}
              >
                {cell ? (
                  <img src={cell.imageUrl} alt={`${idea.title} x ${coord.x} y ${coord.y}`} />
                ) : (
                  <div className="cellPlaceholder">
                    <span />
                  </div>
                )}
                <figcaption>
                  x {coord.x > 0 ? "+" : ""}
                  {coord.x} / y {coord.y > 0 ? "+" : ""}
                  {coord.y}
                </figcaption>
              </figure>
            );
          })}
        </div>
      </div>
    </section>
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

function formatMs(value: number): string {
  if (!value) {
    return "0.0s";
  }
  return `${(value / 1000).toFixed(1)}s`;
}

function paletteStyle(palette: string[]): CSSProperties {
  return {
    "--p0": palette[0],
    "--p1": palette[1],
    "--p2": palette[2],
    "--p3": palette[3]
  } as CSSProperties;
}

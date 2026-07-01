import Link from "next/link";
import type { CSSProperties } from "react";
import type { DemoIdea } from "@/lib/types";

type Props = {
  ideas: DemoIdea[];
};

export function IdeaPicker({ ideas }: Props) {
  return (
    <main className="homeShell">
      <section className="homeIntro">
        <div className="brandLockup">
          <span className="brandMark" />
          <span>Semantic Atlas</span>
        </div>
        <h1>Choose a field. Generate the map live.</h1>
        <p>
          Ten curated worlds, each with two visual axes. Pick one and the grid
          appears as inference completes.
        </p>
      </section>

      <section className="ideaRail" aria-label="Atlas ideas">
        {ideas.map((idea, index) => (
          <Link
            key={idea.id}
            href={`/atlas/${idea.id}`}
            className="ideaTile"
            style={{ "--tile-index": index } as CSSProperties}
          >
            <div className="tileVisual" style={paletteStyle(idea.palette)}>
              <span className="orb orbA" />
              <span className="orb orbB" />
              <span className="axisStroke axisStrokeX" />
              <span className="axisStroke axisStrokeY" />
            </div>
            <div className="tileCopy">
              <span className="tileFamily">{idea.family}</span>
              <h2>{idea.title}</h2>
              <p>{idea.scene}</p>
              <dl className="axisList">
                <div>
                  <dt>X</dt>
                  <dd>
                    {idea.xAxis.negativeLabel} / {idea.xAxis.positiveLabel}
                  </dd>
                </div>
                <div>
                  <dt>Y</dt>
                  <dd>
                    {idea.yAxis.negativeLabel} / {idea.yAxis.positiveLabel}
                  </dd>
                </div>
              </dl>
            </div>
          </Link>
        ))}
      </section>
    </main>
  );
}

function paletteStyle(palette: string[]): CSSProperties {
  return {
    "--p0": palette[0],
    "--p1": palette[1],
    "--p2": palette[2],
    "--p3": palette[3]
  } as CSSProperties;
}

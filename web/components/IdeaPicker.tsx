import Link from "next/link";
import Image from "next/image";
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
        <p>
          Choose a scene.{" "}
          <span>Generate a navigable 5x5 image atlas across two visual axes.</span>
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
              <Image
                src={`/previews/${idea.id}.webp`}
                alt=""
                fill
                sizes="(max-width: 900px) 100vw, 20vw"
                priority={index < 2}
              />
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

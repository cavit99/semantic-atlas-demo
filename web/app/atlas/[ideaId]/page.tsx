import Link from "next/link";
import { notFound } from "next/navigation";
import { LiveGrid } from "@/components/LiveGrid";
import { loadIdea } from "@/lib/ideas";

type Props = {
  params: Promise<{ ideaId: string }>;
};

export default async function AtlasPage({ params }: Props) {
  const { ideaId } = await params;
  const idea = await loadIdea(ideaId);
  if (!idea) {
    notFound();
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <Link href="/" className="backLink">
          All ideas
        </Link>
        <div className="brandLockup">
          <span className="brandMark" />
          <span>Semantic Atlas</span>
        </div>
      </header>
      <LiveGrid idea={idea} />
    </main>
  );
}

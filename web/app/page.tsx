import { IdeaPicker } from "@/components/IdeaPicker";
import { loadIdeas } from "@/lib/ideas";

export default async function Home() {
  const ideas = await loadIdeas();
  return <IdeaPicker ideas={ideas} />;
}

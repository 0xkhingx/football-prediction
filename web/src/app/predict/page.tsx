import type { Metadata } from "next";
import PredictClient from "./PredictClient";

type Props = {
  searchParams: { home?: string; away?: string };
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const home = searchParams.home ?? "Arsenal";
  const away = searchParams.away ?? "Chelsea";
  const og = `/predict/og?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`;
  return {
    title: `Predict ${home} vs ${away}`,
    description: `Fair-play XGBoost call for ${home} vs ${away} — no odds. Research demo, not betting advice.`,
    openGraph: {
      title: `Matchday Fate: ${home} vs ${away}`,
      description: "Every fixture has a fate. Fair-play XGBoost, no odds.",
      images: [{ url: og, width: 1200, height: 630, alt: `${home} vs ${away} prediction card` }],
    },
    twitter: {
      card: "summary_large_image",
      title: `Matchday Fate: ${home} vs ${away}`,
      images: [og],
    },
  };
}

export default function PredictPage() {
  return <PredictClient />;
}

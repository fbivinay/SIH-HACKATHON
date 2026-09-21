import { api } from "@/lib/api";
import StateMap from "@/components/StateMap";
import StateRanking from "@/components/StateRanking";

export const metadata = { title: "States" };

/**
 * The map, then every state ranked.
 *
 * Static: built once and served from the edge, and prefetched in full by
 * every link to it. Nothing here reads the request - the ranking, its order
 * and the term a link asks for all live in StateRanking, in the browser.
 * Measured before: 0.35s to first byte on every visit, and a server round
 * trip on every "Rank by" click.
 */
export default async function StatesPage() {
  // The map's figures are not term-scoped and change nightly; one cached read
  // beside the two lists.
  const [t18, t17, mapStats] = await Promise.all([
    api.states({ ls_term: "18" }),
    api.states({ ls_term: "17" }),
    api.mapStates().catch(() => []),
  ]);

  return (
    <main>
      {/* The first screen is the map and nothing else (owner's call,
          2026-09-19); the /map page it came from is gone. */}
      <section className="map-screen" aria-label="Risk by state, on the map">
        <StateMap stats={mapStats} />
      </section>

      {/* The heading, the term switch, the four totals, the three spending
          bands and the note on how "paid out" is averaged all went on the
          owner's call (2026-09-19). The h1 stays for screen readers. The term
          is still read from ?ls_term, defaulting to the 18th. */}
      <h1 className="sr-only">Where the money went, state by state</h1>

      <section className="shell pt-8">
        <StateRanking byTerm={{ "18": t18, "17": t17 }} />
      </section>
    </main>
  );
}

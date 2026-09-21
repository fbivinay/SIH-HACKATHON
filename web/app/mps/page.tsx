import type { Metadata } from "next";
import { api } from "@/lib/api";
import { cleanName, profileOf, unlistedMembers } from "@/lib/mpProfiles";
import MpDirectory from "@/components/MpDirectory";
import { packRow, type MpCardRow } from "@/lib/mpRows";

export const metadata: Metadata = { title: "Members of Parliament" };

/**
 * Every Member of Parliament in the record, with who they are and what their
 * allocation became, and a way to set up to four side by side.
 *
 * Both terms are rendered on the server and handed over together, so the
 * term switch is a state change and not a round trip - the same reasoning as
 * the overview's switcher (CLAUDE.md §11).
 *
 * Static: nothing reads the request. The term and the members a link picks
 * (?ls_term=, ?compare=) are read in the browser by MpDirectory. The 1,576
 * rows travel as arrays rather than objects (packRow), which is most of the
 * page's weight: field names repeated 1,576 times were a third of it.
 */
export default async function MpsPage() {
  const [t18, t17] = await Promise.all([api.mpDirectory("18"), api.mpDirectory("17")]);

  const toCards = (rows: typeof t18): MpCardRow[] =>
    rows.map((r) => {
      const p = profileOf(r.mp_id);
      const alloc = r.allocated_amount && r.allocated_amount > 0 ? r.allocated_amount : null;
      return {
        id: r.mp_id,
        term: r.ls_term,
        name: cleanName(r.mp_name, p),
        photo: p?.photo ?? null,
        party: p?.party ?? null,
        partyShort: p?.party_short ?? null,
        house: r.house,
        // Rajya Sabha rows carry "Sitting Rajya Sabha" or "Nominated Rajya
        // Sabha" as their constituency - the house again, not a place.
        seat:
          r.house === "Rajya Sabha"
            ? /nominated/i.test(r.constituency ?? "")
              ? "Nominated"
              : null
            : r.constituency,
        state: r.state,
        allocated: r.allocated_amount,
        committed: r.amount_recommended,
        paid: r.total_expenditure,
        idle: r.idle_amount,
        // Two rates, not one (CLAUDE.md §6): committed is recommended over
        // allocated, paid is expenditure over allocated.
        committedRate: alloc && r.amount_recommended !== null ? (r.amount_recommended / alloc) * 100 : null,
        paidRate: alloc && r.total_expenditure !== null ? (r.total_expenditure / alloc) * 100 : null,
        works: r.total_projects,
        inQueue: r.in_queue,
        highRisk: r.high_risk_works,
        // Parliament's status for the seat this record belongs to: a Rajya
        // Sabha member whose 2020-26 seat ended is "Retirement" here even if
        // they were seated again - the new seat is a separate record.
        status: p?.status ?? null,
        unlisted: false,
      };
    });

  // Sitting members the MPLADS portal does not list yet (lib/mpProfiles.ts).
  // Only in the current term: the 17th is over, and its record is complete.
  const unlisted: MpCardRow[] = unlistedMembers().map((m) => ({
    id: m.id,
    term: 18,
    name: m.name,
    photo: m.photo,
    party: m.party,
    partyShort: m.party_short,
    house: m.house,
    seat: m.seat,
    state: m.state,
    allocated: null,
    committed: null,
    paid: null,
    idle: null,
    committedRate: null,
    paidRate: null,
    works: 0,
    inQueue: 0,
    highRisk: 0,
    status: m.status,
    unlisted: true,
  }));

  return (
    <main className="shell py-8">
      <h1 className="display">Members of Parliament</h1>
      <MpDirectory
        packed={{
          "18": [...toCards(t18), ...unlisted].map(packRow),
          "17": toCards(t17).map(packRow),
        }}
      />
    </main>
  );
}

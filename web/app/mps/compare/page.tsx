import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { api, type MpDetail } from "@/lib/api";
import { cleanName, isUnlistedId, profileOf, unlistedMember, type MpProfile } from "@/lib/mpProfiles";
import MpPhoto from "@/components/MpPhoto";
import { formatCount, formatINR } from "@/lib/format";

export const metadata: Metadata = { title: "Compare members" };

type Col = {
  id: string;
  // Sitting but not in the MPLADS record: profile only, every money and works
  // cell reads "Not in MPLADS yet" rather than a zero it never published.
  unlisted: boolean;
  name: string;
  profile: MpProfile | null;
  term: MpDetail["terms"][number];
  works: MpDetail["works"];
  sectors: MpDetail["sectors"];
};

const titleCase = (s: string) =>
  s.toLowerCase().replace(/(^|[\s(-])([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase());

/**
 * Up to four members side by side, one term at a time.
 *
 * One term because a member's two terms are two separate allocations: adding
 * them, or setting one member's 17th against another's 18th, compares
 * nothing. Money is each member's own figure from the MPLADS portal and the
 * rates are computed from it the two ways §6 of CLAUDE.md keeps apart. The
 * bars are relative to the largest value in the row, and only for amounts and
 * counts, where "more" has one meaning; they say nothing about who did well.
 */
export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const term = sp.ls_term === "17" ? "17" : "18";
  const ids = (typeof sp.ids === "string" ? sp.ids.split(",") : [])
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 4);

  const EMPTY_WORKS: MpDetail["works"] = {
    works: 0, completed: 0, pending: 0, high_risk: 0, in_queue: 0,
    sanctioned: 0, flagged_value: 0, districts: 0, agencies: 0,
  };
  const fetched = await Promise.all(
    ids.map((id) =>
      isUnlistedId(id)
        ? Promise.resolve(null)
        : api.mp(id, { ls_term: term }).then((d) => ({ id, d })).catch(() => null)
    )
  );
  const cols: Col[] = fetched.flatMap((f, i): Col[] => {
    if (!f) {
      const m = term === "18" ? unlistedMember(ids[i]) : null;
      if (!m) return [];
      return [{
        id: ids[i],
        unlisted: true,
        name: m.name,
        profile: m,
        term: {
          mp_id: ids[i], ls_term: 18, mp_name: m.name,
          constituency: m.seat ?? (m.house === "Rajya Sabha" ? "Sitting Rajya Sabha" : null),
          state: m.state, house: m.house,
          allocated_amount: null, amount_recommended: null, total_expenditure: null,
          utilization_pct: null, completion_rate_pct: null, unspent_amount: null,
          idle_amount: null, completed_works: null, recommended_works: null, pending_payments: null,
        },
        works: EMPTY_WORKS,
        sectors: [],
      }];
    }
    const t = f.d.terms.find((x) => String(x.ls_term) === term);
    if (!t) return [];
    const profile = profileOf(f.id);
    return [{ id: f.id, unlisted: false, name: cleanName(t.mp_name, profile), profile, term: t, works: f.d.works, sectors: f.d.sectors }];
  });

  const back = `/mps?ls_term=${term}${cols.length ? `&compare=${cols.map((c) => c.id).join(",")}` : ""}`;
  const without = (id: string) => {
    const rest = cols.filter((c) => c.id !== id).map((c) => c.id);
    return rest.length >= 2 ? `/mps/compare?ls_term=${term}&ids=${rest.join(",")}` : `/mps?ls_term=${term}&compare=${rest.join(",")}`;
  };

  if (cols.length < 2) {
    return (
      <main className="shell py-8">
        <Link href={back} className="text-xs link-quiet">&larr; Members of Parliament</Link>
        <h1 className="display mt-4">Compare members</h1>
        <p className="lede !mx-0">
          Pick two to four members on the Members of Parliament page to set them side by side.
        </p>
      </main>
    );
  }

  const rate = (num: number | null, alloc: number | null) =>
    alloc && alloc > 0 && num !== null ? (num / alloc) * 100 : null;

  // A row of the table. `bar` draws a thin ink bar against the row's largest
  // value; `risk` sets the figure in the high-risk colour, the one thing
  // colour is allowed to mean here.
  type Row = {
    label: string;
    note?: string;
    cell: (c: Col) => ReactNode;
    value?: (c: Col) => number | null;
    risk?: boolean;
  };
  const section = (title: string, rows: Row[]) => ({ title, rows });

  const pct = (v: number | null) => (v === null ? "—" : `${v.toFixed(1)}%`);

  const sections = [
    section("Who they are", [
      { label: "Party", cell: (c) => c.profile?.party ?? "—" },
      { label: "House", cell: (c) => c.term.house ?? "—" },
      {
        label: "Seat",
        cell: (c) =>
          c.term.house === "Rajya Sabha"
            ? [/nominated/i.test(c.term.constituency ?? "") ? "Nominated" : null, c.term.state].filter(Boolean).join(", ")
            : [c.term.constituency ? titleCase(c.term.constituency) : null, c.term.state].filter(Boolean).join(", "),
      },
      { label: "Age", cell: (c) => (c.profile?.age ? `${c.profile.age}` : "—") },
      { label: "Education", cell: (c) => c.profile?.qualification ?? "—" },
      { label: "Profession", cell: (c) => (c.profile?.profession ? titleCase(c.profile.profession) : "—") },
      {
        label: "Terms served",
        cell: (c) =>
          c.profile?.terms_served
            ? // Rajya Sabha's count is of Rajya Sabha terms only; a member who
              // sat in the Lok Sabha first would otherwise read as a newcomer.
              c.profile.source === "Rajya Sabha"
              ? `${c.profile.terms_served} in Rajya Sabha${c.profile.rs_term ? ` (seat ${c.profile.rs_term})` : ""}`
              : `${c.profile.terms_served}${c.profile.lok_sabhas ? ` (Lok Sabha ${c.profile.lok_sabhas.replace(/,/g, ", ")})` : ""}`
            : "—",
      },
    ]),
    section("Money", [
      { label: "Allocated", cell: (c) => formatINR(c.term.allocated_amount), value: (c) => c.term.allocated_amount },
      {
        label: "Committed to works",
        note: "Recommended, of allocated",
        cell: (c) => `${formatINR(c.term.amount_recommended)} · ${pct(rate(c.term.amount_recommended, c.term.allocated_amount))}`,
        value: (c) => c.term.amount_recommended,
      },
      {
        label: "Paid out",
        note: "Expenditure, of allocated",
        cell: (c) => `${formatINR(c.term.total_expenditure)} · ${pct(rate(c.term.total_expenditure, c.term.allocated_amount))}`,
        value: (c) => c.term.total_expenditure,
      },
      {
        label: "Never committed",
        note: "Allocated, not attached to any work",
        cell: (c) => formatINR(c.term.idle_amount),
        value: (c) => c.term.idle_amount,
      },
      {
        label: "Awaiting payment",
        note: "Committed to a work, not yet paid",
        cell: (c) => formatINR(c.term.unspent_amount),
        value: (c) => c.term.unspent_amount,
      },
    ]),
    section("Works", [
      { label: "Works on record", cell: (c) => formatCount(c.works.works), value: (c) => c.works.works },
      { label: "Completed", cell: (c) => formatCount(c.works.completed), value: (c) => c.works.completed },
      { label: "Still recommended", cell: (c) => formatCount(c.works.pending), value: (c) => c.works.pending },
      { label: "Completion rate", note: "The portal's own figure", cell: (c) => pct(c.term.completion_rate_pct) },
      { label: "Districts", cell: (c) => formatCount(c.works.districts), value: (c) => c.works.districts },
      { label: "Implementing agencies", cell: (c) => formatCount(c.works.agencies), value: (c) => c.works.agencies },
      {
        label: "Sectors most funded",
        cell: (c) =>
          c.sectors.length ? (
            <ol className="compare__list">
              {c.sectors.slice(0, 3).map((s) => (
                <li key={s.sector}>
                  {s.sector} <span>{formatCount(s.works)}</span>
                </li>
              ))}
            </ol>
          ) : (
            "—"
          ),
      },
    ]),
    section("What to verify", [
      {
        label: "Works to verify",
        note: "Score 40 and above",
        cell: (c) => formatCount(c.works.in_queue),
        value: (c) => c.works.in_queue,
      },
      { label: "High risk", note: "Score 70 and above", cell: (c) => formatCount(c.works.high_risk), value: (c) => c.works.high_risk, risk: true },
      { label: "Sanctioned value flagged", cell: (c) => formatINR(c.works.flagged_value), value: (c) => c.works.flagged_value },
    ]),
  ];

  return (
    <main className="shell py-8">
      <Link href={back} className="text-xs link-quiet">&larr; Members of Parliament</Link>
      <h1 className="display mt-4">Compare members</h1>
      <p className="lede !mx-0 !max-w-3xl">
        {term}th Lok Sabha. A score is a comparison with similar works, not a finding, and a
        member&rsquo;s count of works to verify says where to look, not what was found there.
      </p>

      <div className="compare-wrap mt-6">
        <table className="compare" style={{ ["--cols" as string]: cols.length }}>
          <thead>
            <tr>
              <th scope="col" className="compare__corner">
                <Link href={back} className="btn">+ Add or change</Link>
              </th>
              {cols.map((c, i) => (
                <th key={c.id} scope="col" className="compare__who">
                  <MpPhoto src={c.profile?.photo} name={c.name} size={84} priority={i < 4} />
                  <Link href={`/mp/${encodeURIComponent(c.id)}?ls_term=${term}`} className="compare__name link-quiet">
                    {c.name}
                  </Link>
                  <span className="compare__party">{c.profile?.party_short ?? c.profile?.party ?? ""}</span>
                  <Link href={without(c.id)} className="compare__remove" aria-label={`Remove ${c.name}`}>
                    Remove
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          {sections.map((s) => (
            <tbody key={s.title}>
              <tr className="compare__section">
                <th scope="rowgroup" colSpan={cols.length + 1}>{s.title}</th>
              </tr>
              {s.rows.map((r) => {
                const record = s.title !== "Who they are";
                const vals = r.value ? cols.map((c) => (c.unlisted && record ? 0 : r.value!(c) ?? 0)) : [];
                const max = vals.length ? Math.max(...vals) : 0;
                return (
                  <tr key={r.label}>
                    <th scope="row">
                      {r.label}
                      {r.note && <span className="compare__note">{r.note}</span>}
                    </th>
                    {cols.map((c, i) => (
                      <td key={c.id} className={r.risk && vals[i] > 0 ? "compare__risk" : undefined}>
                        {c.unlisted && record ? (
                          <span className="compare__none">Not in MPLADS yet</span>
                        ) : (
                          r.cell(c)
                        )}
                        {r.value && max > 0 && !(c.unlisted && record) && (
                          <span className="compare__bar" aria-hidden="true">
                            <span style={{ width: `${(vals[i] / max) * 100}%` }} />
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          ))}
        </table>
      </div>

      <p className="mt-4 text-[0.8rem]" style={{ color: "var(--ink-3)" }}>
        Money and completion rate are the MPLADS portal&rsquo;s own per-member figures; works
        are counted from the works it publishes. Party, age, education, profession, terms and
        photographs are from Parliament&rsquo;s member records at sansad.in.
      </p>
    </main>
  );
}

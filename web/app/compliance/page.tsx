import Link from "next/link";
import { api } from "@/lib/api";
import type { ComplianceRule } from "@/lib/api";
import { formatCount } from "@/lib/format";

const STATUS: Record<ComplianceRule["status"], { label: string; note: string; tone: string }> = {
  breached: {
    label: "Breached",
    note: "Works currently fail this check",
    tone: "var(--risk-high)",
  },
  clear: {
    label: "Clear",
    note: "The check runs and nothing fails it",
    tone: "var(--risk-low)",
  },
  inert: {
    label: "Cannot fire",
    note: "The published data cannot satisfy this predicate",
    tone: "var(--risk-medium)",
  },
};

export default async function CompliancePage() {
  const book = await api.compliance();
  const breached = book.rules.filter((r) => r.status === "breached");

  return (
    <main>
      <section className="shell page-head">
        <h1 className="display">What the rules can and cannot catch</h1>
        <p className="lede">
          Every compliance check this system applies, written out with the exact condition
          it tests, so a finding can be argued with rather than believed. Compliance is{" "}
          {book.weight_in_score}% of a work&rsquo;s risk score.
        </p>
      </section>

      <section className="shell">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: "Rules applied", value: formatCount(book.rules.length), note: "Each stated in full below" },
            { label: "Works checked", value: formatCount(book.works_scored), note: "Every scored work" },
            {
              label: "Works breaching",
              value: formatCount(book.works_breaching),
              note: `${((book.works_breaching / book.works_scored) * 100).toFixed(1)}% of those checked`,
              tone: "high" as const,
            },
            {
              label: "Rules that can fire",
              value: `${book.rules.filter((r) => r.status !== "inert").length} of ${book.rules.length}`,
              note: "The rest are stated, not silently dropped",
            },
          ].map((c) => (
            <div key={c.label} className={`stat-card${c.tone ? ` stat-card--${c.tone}` : ""}`}>
              <div className="stat-card__label">{c.label}</div>
              <div className="stat-card__value">{c.value}</div>
              <div className="stat-card__note">{c.note}</div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex flex-col gap-3">
          {book.rules.map((rule) => {
            const s = STATUS[rule.status];
            return (
              <article key={rule.code} className="card rulecard">
                <div className="rulecard__head">
                  <div className="min-w-0">
                    <h2 className="text-[1rem] font-medium">
                      <span
                        className="mr-2 text-[0.8rem]"
                        style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}
                      >
                        {rule.code}
                      </span>
                      {rule.name}
                    </h2>
                    <p className="mt-1.5 text-[0.88rem]" style={{ color: "var(--ink-2)" }}>
                      {rule.checks}
                    </p>
                  </div>
                  <div className="rulecard__count">
                    <span style={{ color: s.tone }}>{formatCount(rule.breaches)}</span>
                    <span className="rulecard__status" style={{ color: s.tone }}>
                      {s.label}
                    </span>
                  </div>
                </div>

                <pre className="rulecard__predicate">{rule.predicate}</pre>

                <div className="rulecard__foot">
                  <span>{rule.basis}</span>
                  <span>
                    Adds {rule.weight} to the compliance component · {s.note}
                  </span>
                </div>

                {rule.breaches > 0 && (
                  <Link href="/alerts" className="link-quiet text-[0.82rem] mt-2 inline-block">
                    See flagged works in the queue
                  </Link>
                )}
              </article>
            );
          })}
        </div>

        <div className="mt-8">
          <h2 className="section-head">What this data cannot answer</h2>
          <p className="lede !mx-0 !max-w-2xl">
            A rule book listing only what passes is the more misleading half. These are
            checks the scheme deserves and the published record cannot support.
          </p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {book.blind_spots.map((b) => (
              <div key={b.name} className="card">
                <h3 className="text-[0.95rem] font-medium">{b.name}</h3>
                <p className="mt-2 text-[0.85rem] leading-relaxed" style={{ color: "var(--ink-2)" }}>
                  {b.why}
                </p>
              </div>
            ))}
          </div>
        </div>

        {breached.length === 0 && (
          <p className="notice mt-6" role="status">
            <span aria-hidden="true">&#9679;</span>
            <span>No rule is currently breached by any scored work.</span>
          </p>
        )}
      </section>
    </main>
  );
}

import { api } from "@/lib/api";

const LABELS: Record<string, string> = {
  escalated: "Escalated for physical verification",
  verified: "Verified — checked and found in order",
  dismissed: "Dismissed — the flag did not hold",
};

function when(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Every decision ever recorded against this work, newest first.
 *
 * The current verdict lives in work_reviews and is overwritten each time
 * somebody changes their mind, which used to take the note explaining the
 * previous decision with it. This reads the append-only trail instead, so the
 * reason a work was escalated survives it later being dismissed.
 */
export default async function ReviewTrail({ workKey }: { workKey: string | null }) {
  if (!workKey) return null;

  let events;
  try {
    ({ events } = await api.reviewHistory(workKey));
  } catch {
    // A history that will not load must not take the work page with it.
    return null;
  }
  if (events.length === 0) {
    return (
      <section className="mt-6">
        <h2 className="text-[0.95rem] font-medium mb-3">Decision trail</h2>
        <p className="text-sm" style={{ color: "var(--ink-3)" }}>
          Nobody has recorded a decision on this work yet.
        </p>
      </section>
    );
  }

  return (
    <section className="mt-6">
      <h2 className="text-[0.95rem] font-medium mb-3">
        Decision trail
        <span className="ml-2 text-[0.8rem] font-normal" style={{ color: "var(--ink-3)" }}>
          {events.length} {events.length === 1 ? "decision" : "decisions"}, newest first
        </span>
      </h2>
      <ol className="trail">
        {events.map((e, i) => (
          <li key={`${e.created_at}-${i}`} className="trail__item">
            <div className="trail__head">
              <span className={`risk-pill risk-pill--${
                e.status === "escalated" ? "high" : e.status === "verified" ? "low" : "pending"
              }`}>
                {e.status}
              </span>
              <span className="trail__when">{when(e.created_at)}</span>
              <span className="trail__who">{e.reviewer?.trim() || "unnamed reviewer"}</span>
            </div>
            <div className="trail__what">{LABELS[e.status] ?? e.status}</div>
            {e.note && <div className="trail__note">{e.note}</div>}
          </li>
        ))}
      </ol>
    </section>
  );
}

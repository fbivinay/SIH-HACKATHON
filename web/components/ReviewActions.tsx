"use client";

import { useActionState, useOptimistic } from "react";
import { submitReview, type ReviewResult } from "@/app/projects/actions";
import type { ReviewStatus } from "@/lib/api";

const DECISIONS: Array<{
  status: Exclude<ReviewStatus, "pending">;
  label: string;
  title: string;
}> = [
  {
    status: "escalated",
    label: "Escalate",
    title: "Send for physical verification",
  },
  {
    status: "verified",
    label: "Verified",
    title: "Checked and found in order",
  },
  {
    status: "dismissed",
    label: "Dismiss",
    title: "Flag does not hold — no action needed",
  },
];

export default function ReviewActions({
  workKey,
  current,
}: {
  workKey: string | null;
  current: ReviewStatus;
}) {
  const [result, formAction, pending] = useActionState<ReviewResult | null, FormData>(
    submitReview,
    null
  );
  // The click is answered at once. The action has to write the decision and
  // then re-render the queue with every cached read expired, which is a full
  // round trip to the API - measured at 1.2s in production and 3s locally -
  // and until now the button sat unchanged and disabled for all of it, which
  // read as the page hanging. The optimistic value is what is shown while
  // that happens, and React drops it for the real one when the action lands;
  // if the write fails, the error below says so and the old state returns.
  const [shown, setShown] = useOptimistic(current);

  // Works loaded before work_key existed cannot be pinned to a decision, and a
  // button that silently does nothing is worse than an absent one.
  if (!workKey) {
    return <span className="review-actions__unavailable">No stable key</span>;
  }

  return (
    <form
      // A form action already runs inside a transition, which is where an
      // optimistic value has to be set.
      action={(fd: FormData) => {
        setShown(String(fd.get("status")) as ReviewStatus);
        // "pending" is a real value here: it is what a cleared work reads as.
        formAction(fd);
      }}
      className="review-actions"
    >
      <input type="hidden" name="work_key" value={workKey} />
      {DECISIONS.map((d) => (
        <button
          key={d.status}
          type="submit"
          name="status"
          // Pressing the decision a work already carries takes it back off:
          // the button is a toggle, not a one-way switch.
          value={shown === d.status ? "pending" : d.status}
          title={shown === d.status ? `${d.label} — press again to clear` : d.title}
          // Not disabled while the write is in flight: next.js runs one
          // client's actions in order and the write is an upsert on
          // work_key, so a second click simply becomes the decision.
          aria-busy={pending || undefined}
          aria-pressed={shown === d.status}
          className={`review-btn review-btn--${d.status}${
            shown === d.status ? " is-current" : ""
          }`}
        >
          {d.label}
        </button>
      ))}
      {result && !result.ok && (
        <span role="alert" className="review-actions__error">
          {result.error}
        </span>
      )}
    </form>
  );
}

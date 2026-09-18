"use client";

import { useActionState } from "react";
import { submitReview, type ReviewResult } from "@/app/alerts/actions";
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

  // Works loaded before work_key existed cannot be pinned to a decision, and a
  // button that silently does nothing is worse than an absent one.
  if (!workKey) {
    return <span className="review-actions__unavailable">No stable key</span>;
  }

  return (
    <form
      action={formAction}
      className="review-actions"
    >
      <input type="hidden" name="work_key" value={workKey} />
      {DECISIONS.map((d) => (
        <button
          key={d.status}
          type="submit"
          name="status"
          value={d.status}
          title={d.title}
          disabled={pending}
          aria-pressed={current === d.status}
          className={`review-btn review-btn--${d.status}${
            current === d.status ? " is-current" : ""
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

"use client";

import { useActionState } from "react";
import { submitReview, type ReviewResult } from "@/app/alerts/actions";
import { REVIEWER_STORAGE_KEY } from "@/components/ReviewerName";
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
      onSubmit={(e) => {
        // Read the name at submit time rather than holding it in state: the
        // field lives in a different component and may change between renders.
        let reviewer = "";
        try {
          reviewer = window.localStorage.getItem(REVIEWER_STORAGE_KEY) ?? "";
        } catch {
          /* unnamed reviewer */
        }
        const input = e.currentTarget.elements.namedItem("reviewer");
        if (input instanceof HTMLInputElement) input.value = reviewer;
      }}
    >
      <input type="hidden" name="work_key" value={workKey} />
      <input type="hidden" name="reviewer" defaultValue="" />
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

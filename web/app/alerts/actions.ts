"use server";

import { revalidatePath } from "next/cache";
import { postReview } from "@/lib/api";
import type { ReviewStatus } from "@/lib/api";

const ALLOWED: ReadonlyArray<Exclude<ReviewStatus, "pending">> = [
  "verified",
  "dismissed",
  "escalated",
];

export type ReviewResult = { ok: true } | { ok: false; error: string };

/**
 * Record a decision on one work.
 *
 * A server action rather than a fetch from the browser so REVIEW_TOKEN stays on
 * the server. That protects the API from anonymous writes; it does not
 * authenticate the person clicking, which this prototype does not do at all —
 * hence `reviewer`, a self-declared name kept so a decision is at least
 * attributable in the record.
 */
export async function submitReview(
  _prev: ReviewResult | null,
  formData: FormData
): Promise<ReviewResult> {
  const workKey = String(formData.get("work_key") ?? "");
  const status = String(formData.get("status") ?? "");
  const note = String(formData.get("note") ?? "").trim();
  const reviewer = String(formData.get("reviewer") ?? "").trim();

  if (!workKey) return { ok: false, error: "This work has no stable key yet." };
  if (!ALLOWED.includes(status as Exclude<ReviewStatus, "pending">)) {
    return { ok: false, error: `Unknown decision "${status}".` };
  }

  try {
    await postReview({
      work_key: workKey,
      status: status as Exclude<ReviewStatus, "pending">,
      note: note || undefined,
      reviewer: reviewer || undefined,
    });
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Review failed." };
  }
  revalidatePath("/alerts");
  return { ok: true };
}

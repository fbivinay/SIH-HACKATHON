import Link from "next/link";
import { formatCount } from "@/lib/format";

/**
 * Previous / Next with the range they move through.
 *
 * "← Previous  Next →" on its own tells a reader nothing about where they are
 * or how much is left: a queue of forty-eight thousand works and a queue of
 * forty look identical from the buttons. The range is the part that is
 * actually useful, so it sits between them rather than as a footnote.
 *
 * `shown` is passed separately from the arithmetic because the last page is
 * short, and `offset + pageSize` would claim rows that are not there.
 */
export default function Pager({
  offset,
  pageSize,
  shown,
  total,
  hrefFor,
  label,
  // An empty noun prints the count alone, which is what the queue wants: the
  // page is the projects, so "48,296 flagged works" restated the page.
  noun = "works",
}: {
  offset: number;
  pageSize: number;
  shown: number;
  total: number | null;
  hrefFor: (offset: number) => string;
  label: string;
  noun?: string;
}) {
  const first = total === 0 ? 0 : offset + 1;
  const last = offset + shown;
  const hasPrev = offset > 0;
  // When the total is unknown, a full page is the only evidence there is more.
  const hasNext = total === null ? shown === pageSize : last < total;

  return (
    <nav className="pager" aria-label={label}>
      {/* Nothing on the first page: a greyed-out "Previous" is a control that
          says the reader could go back, and there is no back. */}
      {hasPrev && (
        <Link href={hrefFor(Math.max(0, offset - pageSize))} className="pager__link">
          ← Previous
        </Link>
      )}

      <span className="pager__range" aria-live="polite">
        <b>
          {formatCount(first)}–{formatCount(last)}
        </b>
        {total !== null ? (
          <>
            {" of "}
            {formatCount(total)}
            {noun ? ` ${noun}` : ""}
          </>
        ) : (
          ` ${noun}`
        )}
      </span>

      {hasNext ? (
        <Link href={hrefFor(offset + pageSize)} className="pager__link">
          Next →
        </Link>
      ) : (
        <span className="pager__link is-disabled">Next →</span>
      )}
    </nav>
  );
}

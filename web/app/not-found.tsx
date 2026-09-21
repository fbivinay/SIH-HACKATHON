import Link from "next/link";

/**
 * Anything that does not exist: a state, district, member or work the record
 * has no entry for, or an address that was never a page. It used to be Next's
 * bare "404 This page could not be found", outside the site's own design.
 *
 * Only a real 404 from the API arrives here (notFoundOr in lib/api.ts); a
 * failing API goes to app/error.tsx instead, and is never cached as missing.
 */
export default function NotFound() {
  return (
    <main className="shell py-16">
      <p className="text-[0.8rem] tabular-nums" style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
        404
      </p>
      <h1 className="display mt-2">Not in the record</h1>
      <p className="lede !mx-0 !max-w-2xl">
        There is nothing at this address. The state, district, member or work it names may be
        spelled differently in the published record, or the link may be out of date.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        <Link href="/" className="btn btn--solid">Overview</Link>
        <Link href="/projects" className="btn">Projects</Link>
        <Link href="/states" className="btn">States</Link>
        <Link href="/mps" className="btn">MPs</Link>
      </div>
      <p className="mt-6 text-[0.85rem]" style={{ color: "var(--ink-3)" }}>
        Or press <kbd className="kbd">/</kbd> and search for it.
      </p>
    </main>
  );
}

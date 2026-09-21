"use client";

import Link from "next/link";

/**
 * When a page fails to render - in practice, the API or the database having
 * a bad moment. Nothing about the failure is cached (a page that throws is
 * not stored), so trying again is the right first move, and it re-renders the
 * page without reloading the site. Replaces Next's bare "Application error".
 */
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="shell py-16">
      <p className="text-[0.8rem]" style={{ fontFamily: "var(--font-data)", color: "var(--ink-3)" }}>
        Could not load
      </p>
      <h1 className="display mt-2">This page did not load</h1>
      <p className="lede !mx-0 !max-w-2xl">
        The record could not be read just now. It is usually a moment&rsquo;s interruption between
        this site and its database, and trying again is enough.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        <button type="button" className="btn btn--solid" onClick={() => reset()}>
          Try again
        </button>
        <Link href="/" className="btn">Overview</Link>
      </div>
    </main>
  );
}

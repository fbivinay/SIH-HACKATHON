/**
 * What a nav click shows while the next page is being rendered.
 *
 * Next renders this the instant a link is clicked and swaps the page in when
 * it streams back, so the click is answered at once whatever the database is
 * doing. Measured before this existed: one to nine seconds of nothing, then
 * the page. Same visual language as the loading cover - a bar and the ghost of
 * the layout that is coming.
 */
export default function Loading() {
  return (
    <main className="pageload" aria-busy="true" aria-label="Loading">
      <div className="shell">
        <div className="pageload__bar">
          <span className="pageload__run" />
        </div>
        <div className="pageload__title" />
        <div className="pageload__lede" />
        <div className="grid gap-3 md:grid-cols-4">
          <div className="pageload__card" />
          <div className="pageload__card" />
          <div className="pageload__card" />
          <div className="pageload__card" />
        </div>
      </div>
    </main>
  );
}

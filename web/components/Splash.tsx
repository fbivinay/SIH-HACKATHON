import Logo from "@/components/Logo";

/**
 * The loading cover: the mark, the name, a bar that fills to 100%, and then it
 * is gone.
 *
 * Entirely CSS. There is no state, no effect and no "use client" here, and that
 * is the design rather than an economy.
 *
 * The first version was a client component that hid itself from a timer in
 * useEffect - which is to say, it hid itself once React had hydrated. On a cold
 * load against a database of 250,000 works, hydration is the slowest thing on
 * the page: measured here, the cover was still reading 0% nearly three seconds
 * in, because the code meant to advance it had not run yet, and it had no way
 * to leave. A loading screen that depends on the thing it is covering for is
 * not a loading screen.
 *
 * From CSS it cannot fail that way. The animation starts at first paint, runs
 * whether or not any script arrives, and ends in `visibility: hidden` with
 * `forwards`, so the cover lifts even if JavaScript never executes. The
 * percentage counts through a registered custom property, so the number is real
 * rather than a picture of one.
 */
export default function Splash() {
  return (
    <div className="splash" aria-hidden="true">
      <div className="splash__inner">
        <Logo size={58} />
        <div className="splash__name">Kasauti</div>
        <div className="splash__sub">MPLADS verification</div>
        <div className="splash__ai">AI powered · Gemini Flash Lite · Isolation Forest · Sentence-BERT</div>
        <div className="splash__track">
          <span className="splash__fill" />
        </div>
        <div className="splash__pct" />
      </div>
    </div>
  );
}

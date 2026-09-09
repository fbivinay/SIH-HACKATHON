/**
 * The mark: a touchstone and the streaks left on it.
 *
 * A jeweller rubs gold against a touchstone and reads the streak to judge the
 * metal. Nothing is destroyed and nothing is accused - the stone only says
 * which pieces are worth assaying, which is exactly the claim this system
 * makes about a work and exactly the claim it refuses to make.
 *
 * Three strokes, staggered and of unequal length, because the streaks a stone
 * carries are the record of what has already been tested - and because unequal
 * bars are the same shape the risk breakdown draws on every queue row.
 *
 * Geometry only: no gradient, no shadow, no bevel. It has to survive at 20px in
 * a browser tab and in one colour on a printed slide.
 */
export default function Logo({ size = 26 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="32" height="32" rx="8" fill="var(--ink)" />
      <g
        stroke="var(--surface)"
        strokeWidth="2.6"
        strokeLinecap="round"
        // Parallel at 45°, offset along the perpendicular so they read as
        // successive strokes on one stone rather than a chevron.
      >
        <path d="M10.4 15.6 L15.6 10.4" />
        <path d="M11 21 L21 11" />
        <path d="M16.4 21.6 L21.6 16.4" />
      </g>
    </svg>
  );
}

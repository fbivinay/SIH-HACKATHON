import Image from "next/image";

/**
 * A member's photograph, or their initials where there is none. The images
 * are Parliament's own, cropped to 4:5 and stored in public/mps by
 * scripts/fetch_mp_profiles.py - sansad.in will not serve them to other sites.
 */
export default function MpPhoto({
  src,
  name,
  size = 64,
  priority = false,
}: {
  src: string | null | undefined;
  name: string;
  size?: number;
  priority?: boolean;
}) {
  const h = Math.round((size * 5) / 4);
  if (!src) {
    const initials = name
      .split(/\s+/)
      .filter((w) => /^[A-Za-z]/.test(w))
      .slice(0, 2)
      .map((w) => w[0].toUpperCase())
      .join("");
    return (
      <span className="mpphoto mpphoto--none" style={{ width: size, height: h }} aria-hidden="true">
        {initials}
      </span>
    );
  }
  return (
    <Image
      src={src}
      alt={`Photograph of ${name}`}
      width={size}
      height={h}
      className="mpphoto"
      // Already 120x150 WebP, a few KB each: optimising them again would only
      // spend the image quota.
      unoptimized
      priority={priority}
      loading={priority ? undefined : "lazy"}
    />
  );
}

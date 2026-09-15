import Image from "next/image";
import logo from "@/public/logo.png";

/**
 * The mark: a K cut from the tricolour, the stone and the House.
 *
 * A jeweller rubs gold against a touchstone and reads the streak to judge the
 * metal. Nothing is destroyed and nothing is accused - the stone only says
 * which pieces are worth assaying, which is exactly the claim this system
 * makes about a work and exactly the claim it refuses to make.
 *
 * A raster (`public/logo.png`, 512px, transparent around the letter, its
 * drop shadow kept as translucent black), so it is the one piece of the
 * interface that carries colour without meaning risk.
 * The same file is the README's logo; `app/icon.png` is the 128px cut of it
 * that Next serves as the favicon.
 */
export default function Logo({ size = 26, priority = false }: { size?: number; priority?: boolean }) {
  return <Image src={logo} width={size} height={size} priority={priority} alt="" aria-hidden="true" />;
}

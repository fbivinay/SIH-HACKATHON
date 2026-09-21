/**
 * A member's name without the tail the MPLADS portal writes into it:
 * "Manish Tewari(17th Lok Sabha)", "Shri Akhilesh Yadav (EX17LS)",
 * "Shri Arjun Ram Meghwal (17LS)EX", "Shri Ramji (2020-26)". The term or the
 * seat's years are shown beside the name wherever they matter, so the name
 * itself need not carry them.
 *
 * Plain module, no "use client" and no profiles: the site search runs in the
 * browser and uses this; server pages prefer Parliament's own spelling
 * (cleanName in lib/mpProfiles.ts), which falls back to this.
 */
export function cleanPortalName(name: string): string {
  return name.replace(/\s*\([^()]*\)\s*[A-Za-z]*\s*$/, "").trim() || name;
}

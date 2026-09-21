import data from "@/data/mp_profiles.json";

/**
 * Who a member is, from Parliament's own records (sansad.in), matched to the
 * members of the MPLADS record by scripts/fetch_mp_profiles.py.
 *
 * Not part of the MPLADS record and never mixed into it: nothing here feeds a
 * figure, a score or a flag. It is the member's public role - party, house,
 * age, education, terms - and a photograph, which the MPLADS portal does not
 * publish at all. Personal contact details in the same records are not read.
 *
 * Server components only: the file is ~430KB, and a page should hand the
 * browser the few fields it shows rather than every member's profile.
 */
export type MpProfile = {
  sansad_id: number;
  source: "Lok Sabha" | "Rajya Sabha";
  name: string;
  party: string | null;
  party_short: string | null;
  gender: string | null;
  age: number | null;
  qualification: string | null;
  profession: string | null;
  terms_served: number | null;
  lok_sabhas?: string | null;
  rs_term?: string | null;
  status: string | null;
  photo: string | null;
};

// A sitting member MPLADS does not list yet: Parliament's profile and where
// they sit, and nothing else - there is no fund record to show.
export type UnlistedMember = MpProfile & {
  house: "Lok Sabha" | "Rajya Sabha";
  seat: string | null;
  state: string | null;
};

const file = data as unknown as {
  profiles: Record<string, MpProfile>;
  unlisted: Record<string, UnlistedMember>;
};
const profiles = file.profiles;

/** Keys are "ls-<sansad id>" / "rs-<sansad id>", never an MPLADS mp_id. */
export const isUnlistedId = (id: string) => /^(ls|rs)-\d+$/.test(id);

export function unlistedMember(id: string): UnlistedMember | null {
  return file.unlisted[id] ?? null;
}

export function unlistedMembers(): Array<UnlistedMember & { id: string }> {
  return Object.entries(file.unlisted).map(([id, m]) => ({ id, ...m }));
}

export const PROFILES_FETCHED_AT = (data as { fetched_at: string }).fetched_at;

export function profileOf(mpId: string): MpProfile | null {
  return profiles[mpId] ?? null;
}

/** "Rahul Gandhi (17th Lok Sabha)", "Shri Ramji (2020-26)" -> the name alone.
 * The portal writes the seat or its years into the name; the page says those
 * separately, so the heading does not need to repeat them. */
export function cleanName(portalName: string, profile: MpProfile | null): string {
  if (profile?.name) return profile.name;
  return portalName.replace(/\s*\(.*?\)\s*\w*$/, "").trim() || portalName;
}

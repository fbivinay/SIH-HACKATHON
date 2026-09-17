/**
 * The scopes the overview can be read at.
 *
 * Its own module because both a server component (the sentence naming the
 * scope) and a client one (the switcher) need it: an export from a
 * "use client" module reaches the server as a client reference, not as the
 * array - a plain value imported across that boundary is silently something
 * else, and `TERMS.find is not a function` is what that looks like.
 */
export const TERMS = [
  { value: "18", label: "18th Lok Sabha", note: "2024–29" },
  { value: "17", label: "17th Lok Sabha", note: "2019–24" },
  { value: "", label: "Both terms", note: "everything on record" },
];

export const termHref = (value: string) => (value ? `/?ls_term=${value}` : "/?ls_term=");

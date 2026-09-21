// /district/<state>/<district>?ls_term=<term> lands here through a rewrite in
// next.config.ts, so the term is part of the path and the desk can be cached.
export { default, generateMetadata } from "../../page";

export async function generateStaticParams() {
  return [];
}

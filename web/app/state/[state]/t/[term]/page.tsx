// /state/<state>?ls_term=<term> lands here through a rewrite in next.config.ts,
// so the term is part of the path and the desk can be cached. Same page.
export { default, generateMetadata } from "../../page";

export async function generateStaticParams() {
  return [];
}

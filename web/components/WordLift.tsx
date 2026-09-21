"use client";

import { useEffect } from "react";

/**
 * Wraps every word of running text in a span, so that only the word under the
 * pointer zooms (owner's call) - CSS can lift an element, not a word.
 *
 * The one thing this must not do is take a text node away from React. React
 * keeps a reference to every text node it rendered and, when the text changes
 * (a new Lok Sabha term re-renders the lede), writes the new value straight
 * into that node. So the original node stays exactly where React put it,
 * emptied, and the word spans are inserted beside it; a MutationObserver
 * watches the original for React's write and rebuilds the spans from it. On
 * navigation React drops whole subtrees, which takes the spans with them.
 *
 * Nor may it touch a text node React has not hydrated yet. The page streams
 * in behind the layout (app/loading.tsx is a Suspense boundary), so this
 * effect runs before most of the page has been matched against its markup,
 * and a node emptied before that is a hydration mismatch - React error #418,
 * and the whole boundary re-rendered from scratch. React marks every node it
 * has hydrated or created with a `__reactFiber$…` property, so only marked
 * nodes are wrapped, and the sweep repeats for a few seconds after load to
 * catch the boundaries that hydrate late.
 *
 * Not touched: anything React or the browser may rewrite word by word, or
 * that lifts as one piece already - the counting figures, form controls,
 * buttons, the nav, the ticker, code. Only plain spaces split words: a
 * non-breaking space is in a figure precisely so it does not.
 */

// Text inside these stays as it is. [data-count] is every CountUp: its text is
// rewritten every frame while it counts, and wrapping it meant rebuilding its
// word spans every frame too.
const SKIP =
  "script,style,svg,code,pre,input,textarea,select,option,button,.btn,.review-btn,.nav,.ticker,.wordmark,.figure__value,.stat-card__value,.w,[data-no-wordlift],[data-count]";

const SPLIT = /([ \t\n\r]+)/;

// Original text node -> the spans and spaces made from it.
const made = new WeakMap<Text, Node[]>();

// Object.keys, not `for...in`: React's marker is an own property of the node,
// and for...in also walks every enumerable property the DOM puts on the
// prototype chain - a few hundred per node, for every text node on the page,
// every sweep. Measured 2026-09-21 as most of the unattributed long frames in
// the first ten seconds of every page.
function hasFiber(n: Node | null): boolean {
  if (!n) return false;
  const keys = Object.keys(n);
  for (let i = 0; i < keys.length; i++) if (keys[i].startsWith("__reactFiber$")) return true;
  return false;
}

// React has hydrated or created this text (and so will not re-read its
// markup). A text node that shares its parent with siblings gets a fiber of
// its own; an element whose only child is text gets none - React treats that
// text as the element's content and marks the element instead, and rewrites
// it with textContent, which is why the sweep also sees such nodes come back
// through the observer as the sole child of a marked parent.
function hydrated(n: Node): boolean {
  if (hasFiber(n)) return true;
  const p = n.parentNode;
  return !!p && p.childNodes.length === 1 && hasFiber(p);
}

function render(t: Text, mark: (n: Node) => void) {
  const parent = t.parentNode;
  if (!parent) return;
  for (const n of made.get(t) ?? []) n.parentNode?.removeChild(n);
  const text = t.nodeValue ?? "";
  if (!text.trim()) return;
  const out: Node[] = [];
  for (const piece of text.split(SPLIT)) {
    if (!piece) continue;
    if (SPLIT.test(piece)) {
      out.push(document.createTextNode(piece));
    } else {
      const w = document.createElement("span");
      w.className = "w";
      w.textContent = piece;
      out.push(w);
    }
  }
  made.set(t, out);
  for (const n of out) mark(n);
  // The original keeps its place in the DOM for React and holds no text of
  // its own; the words sit right after it.
  t.nodeValue = "";
  let after: Node = t;
  for (const n of out) {
    parent.insertBefore(n, after.nextSibling);
    after = n;
  }
}

export default function WordLift() {
  useEffect(() => {
    const root = document.querySelector("main")?.parentElement ?? document.body;
    // Our own writes are mutations too; anything we created or emptied is
    // ignored when it comes back through the observer.
    const ours = new WeakSet<Node>();
    const mark = (n: Node) => ours.add(n);

    const wrapUnder = (node: Node) => {
      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
        // Cheapest test first: most text nodes on a settled page are either
        // already done or empty, and closest() on a long selector list is
        // the expensive one.
        acceptNode: (n) => {
          if (made.has(n as Text) || ours.has(n)) return NodeFilter.FILTER_REJECT;
          if (!(n.nodeValue ?? "").trim()) return NodeFilter.FILTER_REJECT;
          const p = n.parentElement;
          if (!p || p.closest(SKIP)) return NodeFilter.FILTER_REJECT;
          return hydrated(n) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        },
      });
      const found: Text[] = [];
      for (let n = walker.nextNode(); n; n = walker.nextNode()) found.push(n as Text);
      for (const t of found) render(t, mark);
      return found.length;
    };

    // Now, and again every 250ms for the ten seconds in which late Suspense
    // boundaries can still be hydrating. Each pass only touches nodes that
    // are hydrated and not yet wrapped, so repeating it is cheap.
    // It stops as soon as the page has loaded and three sweeps in a row found
    // nothing - on most pages that is about a second, not ten.
    wrapUnder(root);
    let quiet = 0;
    const sweep = window.setInterval(() => {
      quiet = wrapUnder(root) === 0 ? quiet + 1 : 0;
      if (quiet >= 3 && document.readyState === "complete") window.clearInterval(sweep);
    }, 250);
    const stop = window.setTimeout(() => window.clearInterval(sweep), 10000);

    const mo = new MutationObserver((records) => {
      for (const r of records) {
        if (r.type === "characterData") {
          const t = r.target as Text;
          // React wrote new text into a node we manage: rebuild its words.
          if (made.has(t) && (t.nodeValue ?? "") !== "") render(t, mark);
        } else {
          for (const n of r.addedNodes) {
            if (ours.has(n)) continue;
            if (n.nodeType === Node.TEXT_NODE) {
              const p = n.parentElement;
              if (p && !p.closest(SKIP) && (n.nodeValue ?? "").trim() && hydrated(n)) render(n as Text, mark);
            } else if (n.nodeType === Node.ELEMENT_NODE) {
              wrapUnder(n);
            }
          }
        }
      }
    });
    mo.observe(root, { childList: true, characterData: true, subtree: true });
    return () => {
      mo.disconnect();
      window.clearInterval(sweep);
      window.clearTimeout(stop);
    };
  }, []);
  return null;
}

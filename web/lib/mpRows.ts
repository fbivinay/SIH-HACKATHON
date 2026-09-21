/**
 * One MPs-page card, and how it travels from the server to the browser.
 *
 * Its own module, not MpDirectory's: a function exported from a "use client"
 * file reaches the server as a client reference, and the page could not call
 * packRow at all ("Attempted to call packRow() from the server"). The same
 * trap as TERMS in lib/terms.ts.
 */
export type MpCardRow = {
  id: string;
  term: number;
  name: string;
  photo: string | null;
  party: string | null;
  partyShort: string | null;
  house: string | null;
  seat: string | null;
  state: string | null;
  allocated: number | null;
  committed: number | null;
  paid: number | null;
  idle: number | null;
  committedRate: number | null;
  paidRate: number | null;
  works: number;
  inQueue: number;
  highRisk: number;
  status: string | null;
  // Sitting, but not in the MPLADS record yet: no money, no works.
  unlisted: boolean;
};

// A row as it travels: the same fields as MpCardRow, in this order, without
// their names and without the two rates, which are worked out on arrival.
export type Packed = [
  string, number, string, string | null, string | null, string | null, string | null,
  string | null, string | null, number | null, number | null, number | null, number | null,
  number, number, number, string | null, 0 | 1,
];

export function packRow(r: MpCardRow): Packed {
  return [
    r.id, r.term, r.name, r.photo, r.party, r.partyShort, r.house, r.seat, r.state,
    r.allocated, r.committed, r.paid, r.idle, r.works, r.inQueue, r.highRisk, r.status,
    r.unlisted ? 1 : 0,
  ];
}

export function unpack(t: Packed): MpCardRow {
  const [id, term, name, photo, party, partyShort, house, seat, state, allocated, committed, paid, idle,
    works, inQueue, highRisk, status, unlisted] = t;
  const alloc = allocated && allocated > 0 ? allocated : null;
  return {
    id, term, name, photo, party, partyShort, house, seat, state, allocated, committed, paid, idle,
    // Two rates, not one (CLAUDE.md §6): committed over allocated, paid over allocated.
    committedRate: alloc && committed !== null ? (committed / alloc) * 100 : null,
    paidRate: alloc && paid !== null ? (paid / alloc) * 100 : null,
    works, inQueue, highRisk, status, unlisted: unlisted === 1,
  };
}


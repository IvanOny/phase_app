// The gym's bar and plates, in pounds: a 45 lb bar; 2.5, 5, 10, 25, 35 and
// 45 lb plates. Logged loads are kilograms; these turn one into the other.
//
// A side is built the way the warm-up builds it: a pair of one big plate,
// sometimes a third no bigger than the pair, and small plates on top that
// come to less than 10 lb. Of the builds that land that close, the one that
// leaves least wins. When none does, the heaviest pair that fits, then big
// plates no larger than it while they fit, then the small ones.
//
// Derived from eight loads, which are how the bar is actually loaded:
//
//    65 kg  side  50    25+25
//  87.5 kg  side  75    25+25+25
//   100 kg  side  87.5  35+35+10+5+2.5     (nothing lands within 10)
//   110 kg  side 100    35+35+25+5
//   120 kg  side 110    35+35+35+5
//   130 kg  side 120    45+45+25+5
//   140 kg  side 132.5  45+45+35+5+2.5
//   160 kg  side 155    45+45+45+10+10     (nothing lands within 10)

export const BAR_LBS = 45;
const BIG = [25, 35, 45];
const SMALL = [10, 5, 2.5];
const LB_TO_KG = 0.45359237;
const EPS = 0.01;

const r2 = n => Math.round(n * 100) / 100;
const sum = ps => ps.reduce((a, p) => a + p, 0);

function smallPlates(rem) {
  const out = [];
  for (const p of SMALL) {
    while (rem >= p - EPS) { out.push(p); rem = r2(rem - p); }
  }
  return out;
}

// Every build that obeys the shape: a lone 25 (the first warm-up plate),
// a pair, or a pair with a third no bigger.
const BUILDS = [[25]];
for (const p of BIG) {
  BUILDS.push([p, p]);
  for (const q of BIG) if (q <= p) BUILDS.push([p, p, q]);
}

// Pounds on one side -> plates, in the order they go on.
export function sideToPlates(sideLbs) {
  const side = r2(sideLbs);

  let best = null;
  for (const b of BUILDS) {
    const rem = r2(side - sum(b));
    if (rem < -EPS || rem >= 10 - EPS) continue;
    if (!best || rem < best.rem - EPS || (Math.abs(rem - best.rem) < EPS && b.length < best.b.length)) {
      best = { b, rem };
    }
  }
  if (best) return [...best.b, ...smallPlates(best.rem)];

  const pair = [...BIG].reverse().find(p => 2 * p <= side + EPS);
  const base = pair ? [pair, pair] : (side >= 25 - EPS ? [25] : []);
  if (pair) {
    let rem = side - 2 * pair;
    for (const q of [...BIG].reverse()) {
      if (q > pair) continue;
      while (rem >= q - EPS) { base.push(q); rem -= q; }
    }
  }
  return [...base, ...smallPlates(r2(side - sum(base)))];
}

// Kilograms on the bar -> plates a side. The total rounds to the nearest
// 5 lb first: two 2.5s is the smallest step the gym has.
export function platesPerSide(kg) {
  const totalLbs = Math.round((kg / LB_TO_KG) / 5) * 5;
  const side = (totalLbs - BAR_LBS) / 2;
  return { totalLbs, plates: side > 0 ? sideToPlates(side) : [] };
}

// Kilograms on the bar -> pounds on one side, the inverse of sideLbsToKg:
// 52.2 kg -> 115 lb -> 35 a side. 0 when the bar alone is all there is.
export function kgToSideLbs(kg) {
  const totalLbs = Math.round((kg / LB_TO_KG) / 5) * 5;
  return Math.max(0, (totalLbs - BAR_LBS) / 2);
}

// Pounds on one side -> kilograms on the bar, bar included, to 0.1 kg.
// 50 lb a side is 45 + 2 x 50 = 145 lb = 65.8 kg.
export function sideLbsToKg(sideLbs) {
  return Math.round((BAR_LBS + 2 * sideLbs) * LB_TO_KG * 10) / 10;
}

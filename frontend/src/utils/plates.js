// The gym's bar and plates, in pounds: a 45 lb bar; 2.5, 5, 10, 25, 35 and
// 45 lb plates. Logged loads are kilograms; these turn one into the other.
//
// A side is built the way the warm-up builds it: one big plate, then a
// second, then a third, all the same size, and the small plates on top for
// the working set. So the question is only which big plate. The answer is
// the smallest -- 25, then 35, then 45 -- whose three come within 10 lb of
// the side; what is left goes on in 10s, 5s and 2.5s.
//
//    65 kg  side  50    25+25
//  87.5 kg  side  75    25+25+25
//   100 kg  side  87.5  35+35+10+5+2.5    (three 25s leave 12.5 -- too much)
//   120 kg  side 110    35+35+35+5
//   160 kg  side 155    45+45+45+10+10
//
// Derived from those five, which are how the bar is actually loaded.

export const BAR_LBS = 45;
const BIG = [25, 35, 45];
const SMALL = [10, 5, 2.5];
const LB_TO_KG = 0.45359237;
const EPS = 0.01;

// Pounds on one side -> plates, in the order they go on.
export function sideToPlates(sideLbs) {
  const side = Math.round(sideLbs * 100) / 100;
  const big = BIG.find(p => side - 3 * p < 10 - EPS) ?? BIG[BIG.length - 1];
  // At most three of a size, except the largest: nothing bigger to move to.
  let n = Math.floor((side + EPS) / big);
  if (big !== BIG[BIG.length - 1]) n = Math.min(3, n);
  const plates = Array(n).fill(big);
  let rem = Math.round((side - n * big) * 100) / 100;
  for (const p of SMALL) {
    while (rem >= p - EPS) {
      plates.push(p);
      rem = Math.round((rem - p) * 100) / 100;
    }
  }
  return plates;
}

// Kilograms on the bar -> plates a side. The total rounds to the nearest
// 5 lb first: two 2.5s is the smallest step the gym has.
export function platesPerSide(kg) {
  const totalLbs = Math.round((kg / LB_TO_KG) / 5) * 5;
  const side = (totalLbs - BAR_LBS) / 2;
  return { totalLbs, plates: side > 0 ? sideToPlates(side) : [] };
}

// Pounds on one side -> kilograms on the bar, bar included, to 0.1 kg.
// 50 lb a side is 45 + 2 x 50 = 145 lb = 65.8 kg.
export function sideLbsToKg(sideLbs) {
  return Math.round((BAR_LBS + 2 * sideLbs) * LB_TO_KG * 10) / 10;
}

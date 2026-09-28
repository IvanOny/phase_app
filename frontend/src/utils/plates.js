// The gym's bar and plates, in pounds: a 45 lb bar; 2.5, 5, 10, 25, 35 and
// 45 lb plates. Logged loads are kilograms; these turn one into the other.
//
// A side is loaded the way the warm-up builds it, not with the fewest plates.
// The first plate is a 25 (the warm-up), the working set adds another 25, and
// so on up to three. Past three 25s the step becomes a 35. 45s are never
// used. So 65 kg is 25+25, where a fewest-plates count would say 45+5 and
// mean stripping the bar between warm-up and work.

export const BAR_LBS = 45;
const LB_TO_KG = 0.45359237;
const EPS = 0.01;

// Pounds on one side -> plates, in the order they go on.
export function sideToPlates(sideLbs) {
  let rem = Math.round(sideLbs * 100) / 100;
  const plates = [];
  const take = p => { plates.push(p); rem = Math.round((rem - p) * 100) / 100; };
  for (let i = 0; i < 3 && rem >= 25 - EPS; i++) take(25);
  while (rem >= 35 - EPS) take(35);
  if (rem >= 25 - EPS) take(25);          // 25–34 left: a fourth 25, not 10+10+5
  for (const p of [10, 5, 2.5]) while (rem >= p - EPS) take(p);
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

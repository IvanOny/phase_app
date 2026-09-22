// Month arithmetic for everything keyed on 'YYYY-MM': the recovery row, the
// Garmin running row, and the axis they share with the lift trend.
//
// All of it is string-in, string-out. A month is a label, not an instant —
// turning it into a Date and back is where time zones get a chance to move
// September into August, and they have taken it before.

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                     'August', 'September', 'October', 'November', 'December'];

export function thisMonth() {
  return new Date().toISOString().slice(0, 7);
}

export function monthOf(dateish) {
  return String(dateish).slice(0, 7);
}

export function shiftMonth(ym, by) {
  const [y, m] = ym.split('-').map(Number);
  const i = (y * 12 + (m - 1)) + by;
  return `${Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, '0')}`;
}

export function monthLabel(ym) {
  const [y, m] = ym.split('-').map(Number);
  return `${MONTHS_LONG[m - 1]} ${y}`;
}

// 'Sep' on its own, 'Sep 26' in January and July — enough to see a year end
// without printing the year eight times.
export function monthTick(ym) {
  const [y, m] = ym.split('-').map(Number);
  const short = MONTHS_SHORT[m - 1];
  return m === 1 || m === 7 ? `${short} ${String(y).slice(2)}` : short;
}

export function monthShort(ym) {
  const [y, m] = ym.split('-').map(Number);
  return `${MONTHS_SHORT[m - 1]} ${y}`;
}

// Every month from `from` to `to`, inclusive — the gaps included. An axis
// that skips the months you didn't train is an axis that lies about how long
// the gap was.
export function monthRange(from, to) {
  const out = [];
  let m = from;
  for (let guard = 0; m <= to && guard < 600; guard++) {
    out.push(m);
    m = shiftMonth(m, 1);
  }
  return out;
}

// Seconds to m:ss or h:mm:ss. Pace forces the short form: 5:58 /km is
// minutes, never hours.
export function clock(sec, pace = false) {
  if (sec == null) return '';
  const s = Math.round(sec);
  if (pace || s < 3600) return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  return `${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`
       + `:${String(s % 60).padStart(2, '0')}`;
}

import { useState, useRef, useEffect } from 'react';
import './FaqPage.css';

const CATEGORIES = [
  {
    label: 'Training concepts',
    items: [
      {
        q: 'What is a phase?',
        a: [
          'A phase is a fixed training block focused on a single primary goal. Phase 1 tracked bench press strength and pull-up volume. Phase 2 is a powerlifting block targeting squat, bench, and deadlift — the three competition lifts.',
          'Each phase tracks its own sessions, e1RM progression, and volume independently. Phases are compared against each other to measure long-term progress.',
        ],
      },
      {
        q: 'What session types exist?',
        a: [
          'Sessions are tagged by type to allow filtering and metric attribution:',
          [
            'squat — squat-focused session; top sets feed the squat e1RM trend',
            'deadlift — deadlift-focused session; top sets feed the deadlift e1RM trend',
            'mixed — session combining two or more of the big three lifts',
            'heavy_bench — max-effort bench session; used for bench e1RM tracking',
            'volume_bench — higher-rep bench work; counted in volume',
            'speed_bench — submaximal speed/technique work',
            'pull — pull-up and upper-back work (maintenance carry-over from Phase 1)',
            'run — aerobic running session',
            'rest — scheduled rest day (logged for HRV tracking without exercises)',
            'other — mobility, conditioning, or anything else',
          ],
        ],
      },
      {
        q: 'What is a top set?',
        a: [
          'A top set is the most demanding set of a session — typically the heaviest load for the given rep range. It is flagged manually (or auto-detected on import) and used exclusively for e1RM calculation.',
          'Only one top set per session contributes to the e1RM chart. If multiple sets are flagged, the one with the highest estimated 1RM wins.',
        ],
      },
      {
        q: 'What is a working set?',
        a: [
          'Working sets are all quality sets counted toward volume — everything except warm-ups and technique singles. A set can be both a top set and a working set.',
          'Volume charts and total session volume are calculated from working sets only.',
        ],
      },
    ],
  },
  {
    label: 'Powerlifting — Phase 2',
    items: [
      {
        q: 'What is Phase 2 tracking?',
        a: [
          'Phase 2 is a powerlifting block: squat, bench press, and deadlift. The goal is to increase your total (the sum of all three lifts) while tracking progress toward an official sport classification.',
          'Bench and pull-ups are still logged as secondary exercises — they appear in sessions normally but the dashboard emphasis shifts to the three competition lifts.',
          'Phase 2 has no fixed end date. It ends when you hit your classification target.',
        ],
      },
      {
        q: 'How is the powerlifting total calculated?',
        a: [
          'The current total shown in the dashboard is the running cumulative best: the highest e1RM (or confirmed 1RM) seen so far for each lift, added together.',
          'This differs from a competition total, where all three attempts happen on the same day. The training total gives a realistic picture of your current capacity across the phase.',
          'If you log a confirmed 1RM for a lift (e.g. after a true max attempt), it overrides the e1RM estimate for that lift if it is higher.',
        ],
      },
      {
        q: 'What is a confirmed 1RM and when should I use it?',
        a: [
          'A confirmed 1RM is a manually entered actual one-rep max — for example, after a max-effort single or a competition attempt.',
          'The app tracks two values per lift: the estimated 1RM (e1RM, derived from top sets using the Epley formula) and any confirmed 1RM you enter manually. The higher of the two is used for the total and classification.',
          'Use it when you successfully complete a true single — it anchors the trend more accurately than estimation from higher-rep sets.',
        ],
      },
      {
        q: 'How does bodyweight affect the GL score?',
        a: [
          'IPF GL Points are bodyweight-adjusted — the same total scores differently at different bodyweights. A 2 kg change in bodyweight shifts your GL score even if your total stays constant.',
          'Bodyweight is optional per session. When logged, it updates the GL calculation immediately. When not logged, the app uses your most recent logged weight as the fallback.',
          'Log bodyweight on days when you weigh yourself — you do not need to log it every session.',
        ],
      },
      {
        q: 'What is the Lift Trend chart showing?',
        a: [
          'The chart shows four lines over time:',
          [
            'Squat (indigo) — running best squat e1RM',
            'Bench (cyan) — running best bench e1RM',
            'Deadlift (emerald) — running best deadlift e1RM',
            'Total (amber dashed) — sum of the three running bests',
          ],
          '"Running best" means each line only moves up, never down. It shows the cumulative progress of each lift across the entire phase — not just what you did that session.',
          'Hovering or tapping a dot shows both the running best and the actual session e1RM for that day, so you can see if a session was a new PR.',
        ],
      },
    ],
  },
  {
    label: 'Classification system',
    items: [
      {
        q: 'What is UPF classification?',
        a: [
          'UPF (Ukrainian Powerlifting Federation) is the IPF affiliate in Ukraine. It uses a sport classification ladder inherited from the Soviet system:',
          [
            'Class 3 — entry-level competitive standard',
            'Class 2 — intermediate competitive',
            'Class 1 — advanced competitive',
            'Candidate Master (КМС) — near-elite',
            'Master of Sport (МС) — elite national level',
          ],
          'Each class has a minimum total (squat + bench + deadlift) that depends on your bodyweight category. The app tracks your gap to the next class and automatically advances the target once you achieve it.',
        ],
      },
      {
        q: 'Which bodyweight category does the app use?',
        a: [
          'UPF and IPF use men\'s weight categories of 74 kg and 83 kg (among others). The app places you in 74 kg if your logged bodyweight is ≤ 74 kg, and 83 kg if it is above that.',
          'If your bodyweight changes enough to cross the category boundary, the classification thresholds update immediately when the new weight is logged.',
          'The current phase targets the 74–83 kg range.',
        ],
      },
      {
        q: 'What are IPF GL Points?',
        a: [
          'IPF GL Points (Goodlift Points) are a bodyweight-adjusted scoring system introduced by the IPF in 2020 to replace the Wilks formula. They allow fair comparison between lifters of different bodyweights.',
          'Formula: GL = Total × 100 ÷ (A − B × e^(−C × bodyweight)), where A, B, C are published IPF coefficients for men, classic raw, full power.',
          'The GL scale used in this app:',
          [
            '< 50 pts — Untrained',
            '50–74 pts — Beginner',
            '75–99 pts — Recreational',
            '100–124 pts — Intermediate',
            '125–149 pts — Advanced',
            '150–174 pts — National-level',
            '175+ pts — World-class',
          ],
          'The display shows your current score, label, and how many points you need to reach the next level.',
        ],
      },
      {
        q: 'UPF vs IPF GL — which should I use?',
        a: [
          'Use the toggle to switch between the two views. They answer different questions:',
          [
            'UPF — "How many kg do I need to hit Class 3?" Concrete, actionable, tied to Ukrainian federation standards',
            'IPF GL — "How do I rank relative to all lifters worldwide?" Bodyweight-adjusted, useful for comparing progress across weight categories or over time if your weight changes',
          ],
          'Both update automatically as you log sessions. There is no "correct" one — they are complementary.',
        ],
      },
    ],
  },
  {
    label: 'Charts & metrics',
    items: [
      {
        q: 'How is e1RM calculated?',
        a: [
          'Estimated one-rep max uses the Epley formula:',
          'e1RM = load × (1 + reps ÷ 30)',
          'It is derived from the top set of each heavy_bench session. Speed and volume bench sessions are excluded — they use submaximal loads that overestimate the true 1RM.',
        ],
      },
      {
        q: 'What do the dot colors on the e1RM chart mean?',
        a: [
          'Dot color encodes the rep range of the top set, giving context to each e1RM estimate:',
          [
            'Indigo — ≤2 reps (near-maximal; most accurate estimate)',
            'Cyan — 3 reps',
            'Emerald — 4 reps',
            'Amber — ≥5 reps (volume range; estimate less reliable)',
          ],
          'Dot size scales proportionally with rep count — heavier singles appear as smaller dots.',
        ],
      },
      {
        q: 'What is volume and how is it shown?',
        a: [
          'Volume is the total mechanical work performed: sum of (load × reps) across all working sets for a given exercise in a session, expressed in kg·reps.',
          'For bodyweight exercises the load is zero, so volume is shown as total reps instead. The chart also displays a second bar for the top set (max reps in a single set) to track intensity alongside volume.',
          'The bench press volume chart can be filtered to heavy, volume, or speed sessions independently.',
        ],
      },
      {
        q: 'What is HRV readiness?',
        a: [
          'HRV readiness is a 0–10 recovery score logged per session, pulled from the Elite HRV app. It reflects autonomic nervous system status on that morning.',
          'Higher scores indicate better recovery. Tracking it alongside e1RM and volume helps identify whether performance dips correlate with poor recovery.',
        ],
      },
    ],
  },
  {
    label: 'Data entry',
    items: [
      {
        q: 'How do I log a session?',
        a: [
          'Tap the + button in the bottom-right corner to open the data entry panel. Two methods are available:',
          [
            'Screenshot import — drop or paste a photo of your workout log; the app extracts exercises and sets automatically using AI, which you can review and correct before saving',
            'Manual entry — coming later; for now use screenshot import or edit existing sessions directly',
          ],
        ],
      },
      {
        q: 'How does screenshot import work?',
        a: [
          'Drop, paste (Ctrl+V), or click to browse a PNG, JPEG, or WEBP image of your workout log. The app sends it to an AI model that identifies exercises, sets, load, and reps.',
          'You review the extracted data in an editable preview — you can correct loads, reps, remove sets or exercises, flip the TOP/W flags, and add HRV readiness and notes before confirming.',
          'All sets detected (including warm-ups) are stored in the database. Only working sets are shown in the session log and counted in volume.',
        ],
      },
      {
        q: 'Can I edit sessions after logging?',
        a: [
          'Yes. Expand any session in the session log to see its exercises and sets. Each set has inline edit and delete controls — tap the pencil icon to edit load, reps, and the TOP/W flags.',
          'The session itself (date, type, HRV, notes) can also be edited from the session row.',
        ],
      },
    ],
  },
];

function AccordionItem({ item, isOpen, onToggle }) {
  const bodyRef = useRef(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (!bodyRef.current) return;
    setHeight(isOpen ? bodyRef.current.scrollHeight : 0);
  }, [isOpen]);

  return (
    <div className={`faq-item${isOpen ? ' faq-item--open' : ''}`}>
      <button className="faq-question" onClick={onToggle} aria-expanded={isOpen}>
        <span>{item.q}</span>
        <span className="faq-chevron" aria-hidden="true" />
      </button>
      <div className="faq-body" style={{ height }} aria-hidden={!isOpen}>
        <div ref={bodyRef} className="faq-answer">
          {item.a.map((block, i) =>
            Array.isArray(block) ? (
              <ul key={i} className="faq-list-block">
                {block.map((line, j) => {
                  const [label, ...rest] = line.split(' — ');
                  return (
                    <li key={j}>
                      {rest.length ? <><strong>{label}</strong>{' — '}{rest.join(' — ')}</> : line}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p key={i}>{block}</p>
            )
          )}
        </div>
      </div>
    </div>
  );
}

export default function FaqPage({ onBack }) {
  const [openSet, setOpenSet] = useState(new Set());
  const totalItems = CATEGORIES.reduce((n, c) => n + c.items.length, 0);
  const allOpen = openSet.size === totalItems;

  const allKeys = CATEGORIES.flatMap((cat, ci) => cat.items.map((_, ii) => `${ci}-${ii}`));

  function toggle(key) {
    setOpenSet(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  function toggleAll() {
    setOpenSet(allOpen ? new Set() : new Set(allKeys));
  }

  return (
    <div className="faq-page">
      <div className="faq-header">
        <button className="btn btn-ghost faq-back" onClick={onBack}>← Back</button>
        <span className="card-title" style={{ marginBottom: 0 }}>FAQ</span>
        <button className="faq-toggle-all" onClick={toggleAll}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>

      <div className="faq-categories">
        {CATEGORIES.map((cat, ci) => (
          <section key={ci} className="faq-category">
            <div className="faq-category-label">{cat.label}</div>
            <div className="faq-items">
              {cat.items.map((item, ii) => {
                const key = `${ci}-${ii}`;
                return (
                  <AccordionItem
                    key={key}
                    item={item}
                    isOpen={openSet.has(key)}
                    onToggle={() => toggle(key)}
                  />
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

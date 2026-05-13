import { useState, useRef, useEffect } from 'react';
import './FaqPage.css';

const CATEGORIES = [
  {
    label: 'Training concepts',
    items: [
      {
        q: 'What is a phase?',
        a: [
          'A phase is a fixed training block with a defined start and end date, focused on a single primary goal — bench press strength, pull-up volume, or aerobic running.',
          'Each phase tracks its own sessions, e1RM progression, and volume independently. Phases are compared against each other to measure long-term progress.',
        ],
      },
      {
        q: 'What session types exist?',
        a: [
          'Sessions are tagged by type to allow filtering and metric attribution:',
          [
            'heavy_bench — max-effort bench session; used for e1RM tracking',
            'volume_bench — higher-rep bench work; counted in volume but not e1RM',
            'speed_bench — submaximal speed/technique work; excluded from both e1RM and volume charts by default',
            'pull — pull-up and upper-back work',
            'run — aerobic running session',
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

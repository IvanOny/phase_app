import { useState, useRef } from 'react';
import './FaqPage.css';

const FAQS = [
  {
    q: 'What is a phase?',
    a: 'A phase is a training block with a defined start and end date focused on a specific goal — bench, pull-ups, or running. Each phase tracks its own sessions and progress independently.',
  },
  {
    q: 'How is e1RM calculated?',
    a: 'Estimated one-rep max uses the Epley formula: e1RM = load × (1 + reps / 30). It is calculated from the top set of each bench session.',
  },
  {
    q: 'What counts as a top set?',
    a: 'A top set is the heaviest working set of the session — the set marked is_top_set in the data. It is used for e1RM tracking.',
  },
  {
    q: 'What is volume?',
    a: 'Volume is the total load moved in a session: sum of (load × reps) across all working sets for an exercise.',
  },
  {
    q: 'What do the dot colors on the e1RM chart mean?',
    a: 'Dot color shows the rep range of the top set: indigo ≤2 reps (very heavy), cyan = 3 reps, emerald = 4 reps, amber ≥5 reps (volume work).',
  },
  {
    q: 'How do I log a session?',
    a: 'Tap the + button in the bottom-right corner. You can enter sets manually or import from a screenshot.',
  },
  {
    q: 'What is HRV readiness?',
    a: 'HRV readiness is pulled from the Elite HRV app and logged per session. It reflects your recovery status on that day.',
  },
];

export default function FaqPage({ onBack }) {
  const [openSet, setOpenSet] = useState(new Set());
  const allOpen = openSet.size === FAQS.length;

  function toggle(i) {
    setOpenSet(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function toggleAll() {
    setOpenSet(allOpen ? new Set() : new Set(FAQS.map((_, i) => i)));
  }

  return (
    <div className="faq-page">
      <div className="faq-header">
        <button className="btn btn-ghost" onClick={onBack} style={{ fontSize: 13, padding: '3px 10px' }}>
          ← Back
        </button>
        <span className="card-title" style={{ marginBottom: 0 }}>FAQ</span>
        <button className="faq-toggle-all" onClick={toggleAll}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>
      <div className="faq-list">
        {FAQS.map((item, i) => {
          const isOpen = openSet.has(i);
          return (
            <div key={i} className={`faq-item${isOpen ? ' faq-item--open' : ''}`}>
              <button className="faq-question" onClick={() => toggle(i)}>
                <span>{item.q}</span>
                <span className="faq-chevron">{isOpen ? '▲' : '▼'}</span>
              </button>
              {isOpen && (
                <div className="faq-answer">{item.a}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

import { useState } from 'react';
import './FaqPage.css';

const FAQ_ITEMS = [
  {
    q: 'What is a training phase?',
    a: 'A phase is a focused training block with a defined start and end date and a primary goal — bench press, pull-ups, or aerobic run work. Each phase groups your sessions so you can track progress within that block independently.',
  },
  {
    q: 'What is e1RM?',
    a: 'e1RM (estimated one-rep max) is calculated from your top set using the Epley formula: load × (1 + reps / 30). It gives a consistent strength indicator across different rep ranges, so a 3×100 kg set and a 6×90 kg set can be compared on the same chart.',
  },
  {
    q: 'What do the dot colors on the e1RM chart mean?',
    a: 'Dot color encodes how many reps were in the top set. Indigo = 1–2 reps (very heavy / near-max), cyan = 3 reps, emerald = 4 reps, amber = 5+ reps (volume work). Larger dots = more reps.',
  },
  {
    q: 'What are the session types?',
    a: 'Heavy bench — low-rep max-effort work. Volume bench — higher-rep accumulation. Speed bench — lighter load, bar speed focus. Pull — pull-up-focused session. Run — aerobic cardio session. Other — anything that does not fit the above.',
  },
  {
    q: 'What is HRV readiness?',
    a: 'HRV (Heart Rate Variability) readiness is a 0–10 score from the Elite HRV app reflecting your recovery state that morning. A score ≥ 7 is shown green (ready to push), 5–6.9 yellow (proceed with caution), < 5 red (consider reducing intensity).',
  },
  {
    q: 'How does screenshot import work?',
    a: 'Drop, paste (Ctrl+V), or click to upload a workout screenshot. The app sends it to Claude, which reads the exercises, sets, reps, and loads and returns structured data for you to review and confirm before saving.',
  },
  {
    q: 'What is the Volume chart showing?',
    a: 'For barbell exercises it shows total kg·reps per session (load × reps summed across all working sets). For bodyweight exercises such as pull-ups it shows total reps. Use the type filter chips (heavy / volume / speed) to focus on a specific session kind.',
  },
  {
    q: 'What is the Maintenance tile?',
    a: 'Maintenance tracks two secondary metrics across the phase: pull-up peak reps (the single highest rep set across all pull sessions) and aerobic run pace from formal aerobic tests. These are shown with a delta vs. the previous recorded value.',
  },
  {
    q: 'How do I add a new phase?',
    a: 'Click the + button at the bottom of the phase navigation bar, or use the FAB (floating + button) and switch to the Phase tab. Set a name, type, start date, and end date.',
  },
  {
    q: 'Can I edit or delete a session?',
    a: 'Yes. Expand a session row in the Sessions tile by clicking it. Each exercise and set can be edited inline. Use the pencil icon to edit session metadata (date, type, readiness, notes) and the bin icon to delete.',
  },
];

export default function FaqPage({ onBack }) {
  const [openSet, setOpenSet] = useState(new Set());
  const allOpen = openSet.size === FAQ_ITEMS.length;

  function toggle(i) {
    setOpenSet(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function toggleAll() {
    setOpenSet(allOpen ? new Set() : new Set(FAQ_ITEMS.map((_, i) => i)));
  }

  return (
    <div className="faq-page">
      <div className="faq-header">
        <button className="faq-back-btn" onClick={onBack}>← Back</button>
        <h1 className="faq-title">FAQ</h1>
        <button className="faq-toggle-all" onClick={toggleAll}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>
      <div className="faq-list">
        {FAQ_ITEMS.map((item, i) => {
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

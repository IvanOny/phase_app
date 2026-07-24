import { useRef, useState } from 'react';

// A button that fires only after a deliberate press-and-hold, so a stray tap
// in the calendar grid can't complete or delete an occurrence by accident.
// Shows a left-to-right "charging" fill (see .exq-chip-btn--holding) for the
// hold duration; cancels on early release or if the pointer leaves the button.
const HOLD_MS = 500;

export default function HoldButton({ className = '', title, onActivate, children }) {
  const timer = useRef(null);
  const [holding, setHolding] = useState(false);

  function cancel() {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    setHolding(false);
  }

  function start(e) {
    // Stop the chip's drag from starting, and suppress the touch callout.
    e.stopPropagation();
    e.preventDefault();
    setHolding(true);
    timer.current = setTimeout(() => {
      timer.current = null;
      setHolding(false);
      onActivate();
    }, HOLD_MS);
  }

  return (
    <button
      type="button"
      className={`${className}${holding ? ' exq-chip-btn--holding' : ''}`}
      title={title}
      style={{ '--hold-ms': `${HOLD_MS}ms` }}
      onPointerDown={start}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      onPointerCancel={cancel}
    >
      {children}
    </button>
  );
}

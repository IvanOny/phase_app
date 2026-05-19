import { useState, useEffect, Fragment } from 'react';
import { createSession } from '../../api/client.js';

const SESSION_TYPES = ['heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other'];

const TYPE_COLORS = {
  heavy_bench:  '#7c3aed',
  volume_bench: '#a855f7',
  speed_bench:  '#ec4899',
  run:          '#22c55e',
  pull:         '#3b82f6',
  other:        '#64748b',
};

const DOW_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function normDate(d) {
  if (!d) return '';
  return String(d).split('T')[0];
}

function addDays(dateStr, n) {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function dayOfWeek(dateStr) {
  return new Date(dateStr + 'T12:00:00').getDay(); // 0=Sun
}

function fmtDay(dateStr) {
  return dateStr.slice(8);
}

function fmtMonth(yyyymm) {
  return MONTH_NAMES[parseInt(yyyymm.slice(5, 7), 10) - 1];
}

function formatType(t) {
  return t.replace(/_/g, ' ');
}

function getSessionTopResult(sessionId, exerciseVolumes) {
  for (const ev of (exerciseVolumes ?? [])) {
    const s = ev.sessions?.find(s => s.sessionId === sessionId);
    if (!s) continue;
    if (ev.isBodyweight) {
      const reps = s.sets?.reduce((sum, set) => sum + set.reps, 0) ?? 0;
      return reps ? `${reps} reps` : null;
    }
    if (s.topLoadKg != null) {
      const topSet = s.sets?.find(set => set.isTopSet && set.isWorkingSet);
      return topSet ? `${s.topLoadKg} kg × ${topSet.reps}` : `${s.topLoadKg} kg`;
    }
  }
  return null;
}

export default function PhaseCalendar({
  phase,
  sessions,
  exerciseVolumes,
  activeTypes,
  onSelectSession,
  onSessionCreated,
  onSessionDeleted,
  isAuthenticated,
}) {
  const allTypesActive = !activeTypes || activeTypes.length === SESSION_TYPES.length;
  const [hoveredDate, setHoveredDate] = useState(null);
  const [tappedDate, setTappedDate] = useState(null);
  const [pickerDate, setPickerDate] = useState(null);
  const [pickerType, setPickerType] = useState(SESSION_TYPES[0]);
  const [pickerSession, setPickerSession] = useState(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const today = new Date().toISOString().slice(0, 10);
  const phaseStart = normDate(phase.startDate);
  const phaseEnd   = normDate(phase.endDate);

  const sessionByDate = {};
  sessions.forEach(s => {
    const key = normDate(s.sessionDate);
    if (key) sessionByDate[key] = s;
  });

  // Align grid to Monday of the week containing phaseStart
  const startDow = dayOfWeek(phaseStart);
  const toMonday = startDow === 0 ? -6 : 1 - startDow;
  const gridStart = addDays(phaseStart, toMonday);

  // Align grid end to Sunday of the week containing phaseEnd
  const endDow = dayOfWeek(phaseEnd);
  const toSunday = endDow === 0 ? 0 : 7 - endDow;
  const gridEnd = addDays(phaseEnd, toSunday);

  const totalGridDays = Math.round(
    (new Date(gridEnd + 'T12:00:00') - new Date(gridStart + 'T12:00:00')) / 86400000
  ) + 1;
  const weeks = Math.ceil(totalGridDays / 7);

  // Build grid
  const grid = [];
  for (let w = 0; w < weeks; w++) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const date = addDays(gridStart, w * 7 + d);
      const inPhase = date >= phaseStart && date <= phaseEnd;
      const session = inPhase ? (sessionByDate[date] ?? null) : null;
      const isPast = date < today;
      const isToday = date === today;
      week.push({ date, inPhase, session, isPast, isToday });
    }
    grid.push(week);
  }

  // Assign a month-index to each week (for alternating backgrounds)
  let monthIdx = 0;
  let lastMo = '';
  const weekMonthIdx = grid.map(week => {
    const mo = week.find(d => d.inPhase)?.date.slice(0, 7) ?? lastMo;
    if (mo && mo !== lastMo) { monthIdx++; lastMo = mo; }
    return monthIdx;
  });

  async function handleCreate() {
    if (!pickerDate || creating) return;
    setCreating(true);
    try {
      const session = await createSession({
        phaseId: phase.phaseId,
        sessionDate: pickerDate,
        sessionType: pickerType,
        isPlanned: true,
      });
      onSessionCreated(session);
      setPickerDate(null);
    } finally {
      setCreating(false);
    }
  }

  async function handleDeletePlanned() {
    if (!pickerSession || deleting) return;
    setDeleting(true);
    try {
      await onSessionDeleted(pickerSession.sessionId);
      setPickerSession(null);
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    if (!tappedDate) return;
    function handleOutside(e) {
      if (!e.target.closest('.cal-day')) setTappedDate(null);
    }
    document.addEventListener('click', handleOutside);
    return () => document.removeEventListener('click', handleOutside);
  }, [tappedDate]);

  function handleCellClick(day) {
    if (!day.inPhase) return;
    if (tappedDate && tappedDate !== day.date) setTappedDate(null);

    if (day.session && !day.session.isPlanned) {
      // Desktop: hoveredDate is set on mouseenter, so click navigates directly.
      // Mobile: no hover, so first tap shows tooltip; second tap navigates.
      if (hoveredDate === day.date || tappedDate === day.date) {
        onSelectSession(day.session.sessionId);
        setTappedDate(null);
      } else {
        setTappedDate(day.date);
      }
      return;
    }

    if (day.session?.isPlanned) {
      setPickerSession(day.session);
      setPickerDate(null);
      return;
    }

    // Empty slot — open type picker for future/today (no auth gate on UI)
    if (day.isPast && !day.isToday) return;
    setPickerDate(day.date);
    setPickerSession(null);
    setPickerType(SESSION_TYPES[0]);
  }

  return (
    <div className="phase-calendar">
      <div className="phase-calendar-header">
        <span className="card-title" style={{ marginBottom: 0 }}>Phase Schedule</span>
      </div>

      <div className="phase-calendar-grid-wrap">
      <div className="phase-calendar-grid-scroll">
        {/* Day-of-week headers */}
        <div className="cal-dow-row">
          {DOW_LABELS.map((l, i) => (
            <div key={i} className="cal-dow-header">{l}</div>
          ))}
        </div>

        {/* Week rows with inline month separators */}
        {grid.map((week, wi) => {
          const prevWeekMo = wi > 0
            ? (grid[wi - 1].find(d => d.inPhase)?.date.slice(0, 7) ?? null)
            : null;
          const curMo = week.find(d => d.inPhase)?.date.slice(0, 7) ?? null;
          const showMonthSep = curMo && curMo !== prevWeekMo;
          const isEvenMonth = weekMonthIdx[wi] % 2 === 0;

          return (
            <Fragment key={wi}>
              {showMonthSep && (
                <div className="cal-month-sep">
                  <span className="cal-month-sep-label">{fmtMonth(curMo)}</span>
                </div>
              )}
              <div className="cal-week-row">
                {week.map((day, di) => {
                  const s = day.session;
                  const color = s ? (TYPE_COLORS[s.sessionType] ?? '#64748b') : null;
                  const isHovered = hoveredDate === day.date;
                  const isTapped = tappedDate === day.date;
                  const showTooltip = (isHovered || isTapped) && s && !s.isPlanned;
                  const topResult = showTooltip
                    ? getSessionTopResult(s.sessionId, exerciseVolumes)
                    : null;
                  const tooltipBelow = wi === 0;
                  const isOpenSlot = !s && day.inPhase && (!day.isPast || day.isToday);
                  const isDimmed = !allTypesActive && s && !activeTypes.includes(s.sessionType);

                  return (
                    <div
                      key={di}
                      className={[
                        'cal-day',
                        !day.inPhase              ? 'cal-day--out'        : '',
                        day.inPhase && isEvenMonth ? 'cal-day--mo-even'   : '',
                        day.isToday               ? 'cal-day--today'      : '',
                        day.isPast && !s          ? 'cal-day--empty-past' : '',
                        s && !s.isPlanned         ? 'cal-day--session'    : '',
                        s?.isPlanned              ? 'cal-day--planned'    : '',
                        isOpenSlot                ? 'cal-day--open'       : '',
                        isDimmed                  ? 'cal-day--dimmed'     : '',
                      ].filter(Boolean).join(' ')}
                      style={color ? { '--cal-color': color } : {}}
                      onClick={() => handleCellClick(day)}
                      onMouseEnter={() => day.inPhase && setHoveredDate(day.date)}
                      onMouseLeave={() => setHoveredDate(null)}
                    >
                      <span className="cal-day-num">{fmtDay(day.date)}</span>
                      {s && <span className="cal-day-dot" />}
                      {showTooltip && (
                        <div className={`cal-tooltip${isTapped ? ' cal-tooltip--tapped' : ''}${tooltipBelow ? ' cal-tooltip--below' : ''}`}>
                          {s && <span>{formatType(s.sessionType)}</span>}
                          {topResult && <span>{topResult}</span>}
                          {isTapped && (
                            <button
                              className="cal-tooltip-view-btn"
                              onClick={e => { e.stopPropagation(); onSelectSession(s.sessionId); setTappedDate(null); }}
                            >
                              View log →
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Fragment>
          );
        })}
      </div>
      </div>

      {/* Type picker for new planned session */}
      {pickerDate && (
        <div className="cal-picker">
          <span className="cal-picker-label">
            Plan&nbsp;{fmtDay(pickerDate)}.{pickerDate.slice(5, 7)}
          </span>
          <select
            value={pickerType}
            onChange={e => setPickerType(e.target.value)}
            className="inline-input"
            style={{ fontSize: 12 }}
          >
            {SESSION_TYPES.map(t => (
              <option key={t} value={t}>{formatType(t)}</option>
            ))}
          </select>
          <div className="cal-picker-actions">
            {isAuthenticated ? (
              <button className="btn btn-primary btn-xs" onClick={handleCreate} disabled={creating}>
                {creating ? '…' : 'Add'}
              </button>
            ) : (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Log in to save</span>
            )}
            <button className="btn btn-ghost btn-xs" onClick={() => setPickerDate(null)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Manage planned session */}
      {pickerSession && (
        <div className="cal-picker">
          <span className="cal-picker-label">
            Planned — {formatType(pickerSession.sessionType)},&nbsp;
            {fmtDay(normDate(pickerSession.sessionDate))}.{normDate(pickerSession.sessionDate).slice(5, 7)}
          </span>
          <div className="cal-picker-actions">
            {isAuthenticated && (
              <button
                className="btn btn-ghost btn-xs"
                style={{ color: 'var(--ready-red)' }}
                onClick={handleDeletePlanned}
                disabled={deleting}
              >
                {deleting ? '…' : 'Remove'}
              </button>
            )}
            <button className="btn btn-ghost btn-xs" onClick={() => setPickerSession(null)}>✕</button>
          </div>
        </div>
      )}
    </div>
  );
}

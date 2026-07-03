import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

// ─── Constants ────────────────────────────────────────────────────────────────

const COLOR_PALETTE = ['#a5b4fc', '#86efac', '#fde68a', '#fca5a5', '#c4b5fd', '#7dd3fc', '#fdba74', '#99f6e4', '#f9a8d4'];
const KNOWN_COLORS = { Ivan: '#a5b4fc', Yurii: '#86efac', Benni: '#fde68a' };

function buildColorMap(participants) {
  const map = {};
  const usedColors = new Set(Object.values(KNOWN_COLORS));
  const freePalette = COLOR_PALETTE.filter(c => !usedColors.has(c));
  let idx = 0;
  for (const p of participants) {
    map[p] = KNOWN_COLORS[p] ?? freePalette[idx++ % freePalette.length];
  }
  return map;
}


// ─── API ──────────────────────────────────────────────────────────────────────

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function apiBurpee(method, path, body, token) {
  const url = `${BASE}${path}?token=${encodeURIComponent(token)}`;
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function getBurpeeEntries(token) {
  return apiBurpee('GET', '/v1/burpee', null, token); // returns { entries, me }
}

function logBurpeeEntry(token, { entryDate, reps }) {
  return apiBurpee('POST', '/v1/burpee', { entry_date: entryDate, reps }, token);
}

function deleteBurpeeEntry(token, id) {
  return apiBurpee('DELETE', `/v1/burpee/${id}`, null, token);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function today() { return new Date().toISOString().slice(0, 10); }
function monthOf(d) { return d.slice(0, 7); }
function prevMonthStr(ym) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m - 2);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}
function nextMonthStr(ym) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}
function fmtMonth(ym) {
  const [y, m] = ym.split('-');
  return new Date(+y, +m - 1).toLocaleString('en', { month: 'long', year: 'numeric' });
}
function fmtMonthShort(ym) {
  const [y, m] = ym.split('-');
  return new Date(+y, +m - 1).toLocaleString('en', { month: 'short' });
}
// ─── Derived stats ────────────────────────────────────────────────────────────

function computeStats(entries, currentMonth, participants) {
  const stats = {};
  for (const p of participants) {
    const thisMonthEntries = entries.filter(
      (e) => e.participant === p && monthOf(e.entryDate) === currentMonth,
    );
    const total = thisMonthEntries.reduce((s, e) => s + e.reps, 0);
    const best = thisMonthEntries.reduce((b, e) => Math.max(b, e.reps), 0);
    const days = thisMonthEntries.length;
    stats[p] = {
      total,
      avg: days > 0 ? Math.round(total / days) : 0,
      days,
      best,
    };
  }
  return stats;
}

function computeMonthlyWins(entries, participants) {
  const curMonth = monthOf(today());
  const months = [...new Set(entries.map((e) => monthOf(e.entryDate)))].filter(
    (m) => m < curMonth,
  ).sort();

  return months.map((ym) => {
    const totals = {};
    for (const p of participants) {
      totals[p] = entries
        .filter((e) => e.participant === p && monthOf(e.entryDate) === ym)
        .reduce((s, e) => s + e.reps, 0);
    }
    const maxTotal = Math.max(0, ...Object.values(totals));
    const leaders = participants.filter((p) => totals[p] === maxTotal && maxTotal > 0);
    const winner = leaders.length === 1 ? leaders[0] : null;
    return { ym, winner };
  });
}

function buildChartData(entries, currentMonth) {
  const filtered = entries.filter((e) => monthOf(e.entryDate) === currentMonth);
  const byDay = {};
  for (const e of filtered) {
    const day = e.entryDate.slice(8); // DD
    if (!byDay[day]) byDay[day] = { day };
    byDay[day][e.participant] = e.reps;
  }
  return Object.values(byDay).sort((a, b) => a.day.localeCompare(b.day));
}

// ─── Sub-components ───────────────────────────────────────────────────────────


function ScoreCard({ participant, color, stats, isLeader, isMe, compact }) {

  return (
    <div
      style={{
        flex: 1,
        background: 'var(--bg-elevated, #1a1d27)',
        border: `1.5px solid ${isLeader ? color : 'var(--border, #2a2d3a)'}`,
        borderRadius: 'var(--radius-md, 10px)',
        padding: compact ? '10px 10px' : '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 3,
        boxShadow: isLeader ? `0 0 16px ${color}33` : 'none',
        transition: 'box-shadow 0.2s',
        minWidth: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontWeight: 700, fontSize: compact ? 12 : 15, color }}>{participant}</span>
        {isMe && (
          <span style={{ fontSize: 9, background: color, color: '#333', borderRadius: 4, padding: '1px 4px', fontWeight: 600 }}>
            you
          </span>
        )}
      </div>
      <div style={{ fontSize: compact ? 26 : 36, fontWeight: 800, color: 'var(--text-primary, #fff)', lineHeight: 1.1 }}>
        {stats.total}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary, #aaa)', fontWeight: 600 }}>avg {stats.avg} / day</div>
      <div style={{ fontSize: 11, color: 'var(--text-muted, #888)' }}>
        {stats.days}d · best {stats.best}
      </div>
    </div>
  );
}

function LeadIndicator({ stats, participants, pColors }) {
  if (participants.length < 2) return null;
  const sorted = [...participants].sort((a, b) => stats[b].total - stats[a].total);
  const top = sorted[0];
  const second = sorted[1];
  const margin = stats[top].total - stats[second].total;
  if (margin === 0) {
    return (
      <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-secondary, #aaa)', padding: '4px 0' }}>
        🤝 Tied
      </div>
    );
  }
  return (
    <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 600, color: pColors[top] ?? '#888', padding: '4px 0' }}>
      ⚡ {top} leads by {margin} reps
    </div>
  );
}

function MonthlyWinsRow({ wins, viewMonth, onSelect, currentMonth, pColors }) {
  const allPills = [...wins, { ym: currentMonth, winner: null, isCurrent: true }];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, overflowX: 'auto', paddingBottom: 4 }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted, #888)', whiteSpace: 'nowrap', flexShrink: 0 }}>
        history:
      </span>
      {allPills.map(({ ym, winner, isCurrent }) => {
        const isActive = ym === viewMonth;
        const wColor = winner ? (pColors[winner] ?? '#888') : null;
        return (
          <span
            key={ym}
            onClick={() => onSelect(ym)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 3,
              background: isActive
                ? (wColor ?? 'var(--text-muted, #888)')
                : wColor ? `${wColor}22` : 'var(--bg-elevated, #1a1d27)',
              border: `1px solid ${wColor ?? 'var(--border, #2a2d3a)'}`,
              color: isActive ? '#333' : wColor ?? 'var(--text-muted, #888)',
              borderRadius: 20,
              padding: '2px 9px',
              fontSize: 12,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              flexShrink: 0,
              cursor: 'pointer',
            }}
          >
            {fmtMonthShort(ym)}{!isCurrent && ` · ${winner ? winner[0] : '–'}`}
          </span>
        );
      })}
    </div>
  );
}

const navBtnStyle = {
  background: 'transparent',
  border: 'none',
  color: 'var(--text-secondary, #aaa)',
  fontSize: 20,
  lineHeight: 1,
  cursor: 'pointer',
  padding: '0 6px',
};

function BurpeeHorizontalChart({ chartData, label, onPrev, onNext, canGoNext, participants, pColors }) {
  const rowHeight = 28;
  const height = Math.max(chartData.length * rowHeight + 24, 60);
  const axisMax = (p) => {
    const max = Math.max(...chartData.map((d) => d[p] ?? 0), 1);
    return Math.ceil(max / 4) * 4;
  };

  return (
    <div
      style={{
        background: 'var(--bg-elevated, #1a1d27)',
        borderRadius: 'var(--radius-md, 10px)',
        padding: 16,
        marginTop: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <button onClick={onPrev} style={navBtnStyle}>‹</button>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary, #aaa)' }}>{label}</span>
        <button onClick={onNext} disabled={!canGoNext} style={{ ...navBtnStyle, opacity: canGoNext ? 1 : 0.3 }}>›</button>
      </div>
      {!chartData.length && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted, #888)', fontSize: 13, padding: '16px 0' }}>
          No entries this month
        </div>
      )}
      <div style={{ display: 'flex', gap: 8 }}>
        {participants.map((p, i) => {
          const color = pColors[p] ?? '#888';
          const showYAxis = i === 0;
          return (
            <div key={p} style={{ flex: 1, minWidth: 0 }}>
              <ResponsiveContainer width="100%" height={height}>
                <BarChart
                  data={chartData}
                  layout="vertical"
                  barSize={12}
                  margin={{ top: 0, right: 8, bottom: 0, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #2a2d3a)" horizontal={false} />
                  <XAxis
                    type="number"
                    domain={[0, axisMax(p)]}
                    tick={{ fill: 'var(--text-muted, #888)', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="day"
                    tick={{ fill: 'var(--text-muted, #888)', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={showYAxis ? 24 : 0}
                    tickFormatter={showYAxis ? undefined : () => ''}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-elevated, #1a1d27)',
                      border: '1px solid var(--border, #2a2d3a)',
                      borderRadius: 6,
                      fontSize: 12,
                      color: 'var(--text-primary, #fff)',
                    }}
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    formatter={(value) => [value, p]}
                  />
                  <Bar dataKey={p} fill={color} radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function BurpeeChallenge({ token }) {
  const [me, setMe] = useState(null);
  const [entries, setEntries] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [pColors, setPColors] = useState(KNOWN_COLORS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [repsInput, setRepsInput] = useState('');
  const [logDate, setLogDate] = useState(today);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [viewMonth, setViewMonth] = useState(() => monthOf(today()));
  const [selectedParticipants, setSelectedParticipants] = useState(() => {
    try {
      const saved = localStorage.getItem('burpee_selected_participants');
      if (saved) return JSON.parse(saved);
    } catch {}
    return [];
  });
  const [pillOrder, setPillOrder] = useState(() => {
    try {
      const saved = localStorage.getItem('burpee_pill_order');
      if (saved) return JSON.parse(saved);
    } catch {}
    return [];
  });
  const [dragIdx, setDragIdx] = useState(null);

  const currentMonth = monthOf(today());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBurpeeEntries(token);
      setEntries(data.entries);
      setMe(data.me);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    async function fetchParticipants() {
      try {
        const data = await apiBurpee('GET', '/v1/burpee/participants', null, token);
        const list = data.participants || [];
        setParticipants(list);
        setPColors(buildColorMap(list));
        setSelectedParticipants((prev) => {
          const valid = prev.filter((p) => list.includes(p));
          if (valid.length > 0) return valid;
          return list;
        });
        setPillOrder((prev) => {
          const kept = prev.filter((p) => list.includes(p));
          const added = list.filter((p) => !kept.includes(p));
          return [...kept, ...added];
        });
      } catch {
        // fallback: participants will stay empty, derived from entries on next render
      }
    }
    fetchParticipants();
  }, [token]);

  useEffect(() => {
    if (me) {
      setSelectedParticipants(prev =>
        prev.includes(me) ? prev : [...prev, me]
      );
    }
  }, [me]);

  // Pre-fill input with existing entry for the selected date
  const myDateEntry = me
    ? entries.find((e) => e.participant === me && e.entryDate === logDate)
    : null;

  useEffect(() => {
    if (myDateEntry) {
      setRepsInput(String(myDateEntry.reps));
    } else {
      setRepsInput('');
    }
  }, [myDateEntry?.id, logDate]);

  async function handleLog(e) {
    e.preventDefault();
    const reps = parseInt(repsInput, 10);
    if (!reps || reps < 1 || reps > 300) return;
    setSaving(true);
    setSaveError(null);
    try {
      if (myDateEntry) {
        await deleteBurpeeEntry(token, myDateEntry.id);
      }
      await logBurpeeEntry(token, { entryDate: logDate, reps });
      await load();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!myDateEntry) return;
    setSaving(true);
    setSaveError(null);
    try {
      await deleteBurpeeEntry(token, myDateEntry.id);
      setRepsInput('');
      await load();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary, #aaa)' }}>
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444', padding: 24, textAlign: 'center' }}>
        {error}
      </div>
    );
  }

  const orderedAll = pillOrder.length > 0
    ? pillOrder.filter(p => participants.includes(p) || p === me)
    : (me ? [me, ...participants.filter(p => p !== me)] : participants);

  const myView = orderedAll.filter(p => p === me || selectedParticipants.includes(p));

  function toggleParticipant(p) {
    if (p === me) return;
    setSelectedParticipants(prev => {
      const next = prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p];
      localStorage.setItem('burpee_selected_participants', JSON.stringify(next));
      return next;
    });
  }

  function handleDragStart(i) { setDragIdx(i); }
  function handleDragOver(e) { e.preventDefault(); }
  function handleDrop(i) {
    if (dragIdx === null || dragIdx === i) { setDragIdx(null); return; }
    const next = [...orderedAll];
    const [moved] = next.splice(dragIdx, 1);
    next.splice(i, 0, moved);
    setPillOrder(next);
    localStorage.setItem('burpee_pill_order', JSON.stringify(next));
    setDragIdx(null);
  }
  const stats = computeStats(entries, viewMonth, participants);
  const wins = computeMonthlyWins(entries, participants);
  const chartData = buildChartData(entries, viewMonth);

  const meColor = pColors[me] ?? '#6366f1';

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '16px 16px 40px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary, #fff)' }}>
            🔥 БУРЧИК CHALLENGE
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginTop: 2 }}>
            3 min AMRAP Burpees
          </div>
        </div>
      </div>

      {/* Participant pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {orderedAll.map((p, i) => {
          const active = p === me || selectedParticipants.includes(p);
          const color = pColors[p] ?? '#888';
          const isDragging = dragIdx === i;
          return (
            <button
              key={p}
              draggable
              onDragStart={() => handleDragStart(i)}
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(i)}
              onDragEnd={() => setDragIdx(null)}
              onClick={() => toggleParticipant(p)}
              style={{
                background: active ? color : 'transparent',
                border: `1.5px solid ${active ? color : 'var(--border, #2a2d3a)'}`,
                borderRadius: 20,
                color: active ? '#333' : 'var(--text-muted, #888)',
                fontSize: 13,
                fontWeight: 600,
                padding: '4px 14px',
                cursor: 'grab',
                opacity: isDragging ? 0.4 : 1,
                transition: 'opacity 0.15s',
              }}
            >
              {p}
            </button>
          );
        })}
      </div>

      {/* Scoreboard */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: myView.length > 3 ? 'repeat(2, 1fr)' : `repeat(${myView.length}, 1fr)`,
        gap: myView.length > 3 ? 6 : 10,
        marginBottom: 8,
      }}>
        {myView.filter(p => stats[p]).map((p) => (
          <ScoreCard
            key={p}
            participant={p}
            color={pColors[p] ?? '#888'}
            stats={stats[p]}
            isLeader={stats[p].total > 0 && myView.every(o => !stats[o] || o === p || stats[p].total >= stats[o].total)}
            isMe={p === me}
            compact={myView.length > 3}
          />
        ))}
      </div>
      <LeadIndicator stats={stats} participants={myView} pColors={pColors} />

      {/* Monthly wins */}
      <MonthlyWinsRow wins={wins} viewMonth={viewMonth} onSelect={setViewMonth} currentMonth={currentMonth} pColors={pColors} />

      {/* Horizontal chart */}
      <BurpeeHorizontalChart
        chartData={chartData}
        label={fmtMonth(viewMonth)}
        onPrev={() => setViewMonth(prevMonthStr(viewMonth))}
        onNext={() => setViewMonth(nextMonthStr(viewMonth))}
        canGoNext={viewMonth < currentMonth}
        participants={myView}
        pColors={pColors}
      />

      {/* Log form */}
      <div
        style={{
          background: 'var(--bg-elevated, #1a1d27)',
          border: `1px solid ${meColor}44`,
          borderRadius: 'var(--radius-md, 10px)',
          padding: '14px 16px',
          marginTop: 12,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: meColor, marginBottom: 10 }}>
          Log for {me}
        </div>
        <form onSubmit={handleLog} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="date"
            value={logDate}
            max={today()}
            onChange={(e) => setLogDate(e.target.value)}
            style={{
              flex: 1,
              minWidth: 0,
              padding: '8px 10px',
              borderRadius: 'var(--radius-md, 8px)',
              border: '1px solid var(--border, #2a2d3a)',
              background: 'var(--bg-elevated, #1a1d27)',
              color: 'var(--text-primary, #fff)',
              fontSize: 13,
              outline: 'none',
              colorScheme: 'dark',
            }}
          />
          <input
            type="number"
            min={1}
            max={300}
            placeholder="reps"
            value={repsInput}
            onChange={(e) => setRepsInput(e.target.value)}
            style={{
              width: 68,
              padding: '8px 10px',
              borderRadius: 'var(--radius-md, 8px)',
              border: `1px solid ${repsInput ? meColor + '88' : 'var(--border, #2a2d3a)'}`,
              background: 'var(--bg-elevated, #1a1d27)',
              color: 'var(--text-primary, #fff)',
              fontSize: 15,
              fontWeight: 600,
              outline: 'none',
              textAlign: 'center',
            }}
          />
          <button
            type="submit"
            disabled={saving || !repsInput}
            style={{
              background: repsInput ? meColor : 'var(--border, #2a2d3a)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md, 8px)',
              padding: '8px 16px',
              fontSize: 13,
              fontWeight: 600,
              cursor: saving || !repsInput ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1,
              transition: 'background 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {myDateEntry ? 'Update' : 'Save'}
          </button>
          {myDateEntry && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={saving}
              title="Delete entry"
              style={{
                background: 'transparent',
                border: '1px solid var(--border, #2a2d3a)',
                borderRadius: 'var(--radius-md, 8px)',
                color: 'var(--text-muted, #888)',
                fontSize: 16,
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: saving ? 'not-allowed' : 'pointer',
                padding: 0,
              }}
            >
              ×
            </button>
          )}
        </form>
        {saving && (
          <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginTop: 6 }}>Saving…</div>
        )}
        {saveError && (
          <div style={{ fontSize: 12, color: '#ef4444', marginTop: 6 }}>{saveError}</div>
        )}
      </div>
    </div>
  );
}

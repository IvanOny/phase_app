import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

// ─── Constants ────────────────────────────────────────────────────────────────

const PARTICIPANTS = ['Ivan', 'Yurii', 'Benni'];
const P_COLORS = { Ivan: '#6366f1', Yurii: '#10b981', Benni: '#f59e0b' };


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

function computeStats(entries, currentMonth) {
  const stats = {};
  for (const p of PARTICIPANTS) {
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

function computeMonthlyWins(entries) {
  // Group all completed months (not current)
  const curMonth = monthOf(today());
  const months = [...new Set(entries.map((e) => monthOf(e.entryDate)))].filter(
    (m) => m < curMonth,
  ).sort();

  return months.map((ym) => {
    const totals = {};
    for (const p of PARTICIPANTS) {
      totals[p] = entries
        .filter((e) => e.participant === p && monthOf(e.entryDate) === ym)
        .reduce((s, e) => s + e.reps, 0);
    }
    const [a, b] = PARTICIPANTS;
    let winner = null;
    if (totals[a] > totals[b]) winner = a;
    else if (totals[b] > totals[a]) winner = b;
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

function IdentityPicker({ onPick }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 24,
        padding: 24,
        background: 'var(--bg-elevated, #1a1d27)',
      }}
    >
      <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--text-primary, #fff)', textAlign: 'center' }}>
        🔥 БУРЧИК CHALLENGE
      </div>
      <div style={{ fontSize: 16, color: 'var(--text-secondary, #aaa)' }}>Who are you?</div>
      <div style={{ display: 'flex', gap: 16 }}>
        {PARTICIPANTS.map((p) => (
          <button
            key={p}
            onClick={() => onPick(p)}
            style={{
              background: P_COLORS[p],
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md, 10px)',
              padding: '20px 36px',
              fontSize: 22,
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: `0 4px 20px ${P_COLORS[p]}55`,
              transition: 'transform 0.1s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function ScoreCard({ participant, stats, isLeader, isMe, compact }) {
  const color = P_COLORS[participant];

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
          <span style={{ fontSize: 9, background: color, color: '#fff', borderRadius: 4, padding: '1px 4px', fontWeight: 600 }}>
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

function LeadIndicator({ stats, participants }) {
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
    <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 600, color: P_COLORS[top], padding: '4px 0' }}>
      ⚡ {top} leads by {margin} reps
    </div>
  );
}

function MonthlyWinsRow({ wins, viewMonth, onSelect, currentMonth }) {
  const allPills = [...wins, { ym: currentMonth, winner: null, isCurrent: true }];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, overflowX: 'auto', paddingBottom: 4 }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted, #888)', whiteSpace: 'nowrap', flexShrink: 0 }}>
        history:
      </span>
      {allPills.map(({ ym, winner, isCurrent }) => {
        const isActive = ym === viewMonth;
        return (
          <span
            key={ym}
            onClick={() => onSelect(ym)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 3,
              background: isActive
                ? (winner ? P_COLORS[winner] : 'var(--text-muted, #888)')
                : winner ? `${P_COLORS[winner]}22` : 'var(--bg-elevated, #1a1d27)',
              border: `1px solid ${winner ? P_COLORS[winner] : 'var(--border, #2a2d3a)'}`,
              color: isActive ? '#fff' : winner ? P_COLORS[winner] : 'var(--text-muted, #888)',
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

function BurpeeHorizontalChart({ chartData, label, onPrev, onNext, canGoNext, participants }) {
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
          const color = P_COLORS[p];
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [repsInput, setRepsInput] = useState('');
  const [logDate, setLogDate] = useState(today);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [viewMonth, setViewMonth] = useState(() => monthOf(today()));
  const [selectedParticipants, setSelectedParticipants] = useState(PARTICIPANTS);

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

  const myView = [me, ...PARTICIPANTS.filter(p => p !== me && selectedParticipants.includes(p))]
    .filter(p => selectedParticipants.includes(p));

  function toggleParticipant(p) {
    if (p === me) return; // can't remove yourself
    setSelectedParticipants(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  }
  const stats = computeStats(entries, viewMonth);
  const wins = computeMonthlyWins(entries);
  const chartData = buildChartData(entries, viewMonth);

  const meColor = P_COLORS[me];

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
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {[me, ...PARTICIPANTS.filter(p => p !== me)].map(p => {
          const active = selectedParticipants.includes(p);
          const color = P_COLORS[p];
          const isMe = p === me;
          return (
            <button
              key={p}
              onClick={() => toggleParticipant(p)}
              style={{
                background: active ? color : 'transparent',
                border: `1.5px solid ${active ? color : 'var(--border, #2a2d3a)'}`,
                borderRadius: 20,
                color: active ? '#fff' : 'var(--text-muted, #888)',
                fontSize: 13,
                fontWeight: 600,
                padding: '4px 14px',
                cursor: isMe ? 'default' : 'pointer',
                opacity: isMe && !active ? 0.5 : 1,
                transition: 'all 0.15s',
              }}
            >
              {p}
            </button>
          );
        })}
      </div>

      {/* Scoreboard */}
      <div style={{ display: 'flex', gap: myView.length > 2 ? 6 : 10, marginBottom: 8 }}>
        {myView.map((p) => (
          <ScoreCard
            key={p}
            participant={p}
            stats={stats[p]}
            isLeader={stats[p].total > 0 && myView.every(o => o === p || stats[p].total >= stats[o].total)}
            isMe={p === me}
            compact={myView.length > 2}
          />
        ))}
      </div>
      <LeadIndicator stats={stats} participants={myView} />

      {/* Monthly wins */}
      <MonthlyWinsRow wins={wins} viewMonth={viewMonth} onSelect={setViewMonth} currentMonth={currentMonth} />

      {/* Horizontal chart */}
      <BurpeeHorizontalChart
        chartData={chartData}
        label={fmtMonth(viewMonth)}
        onPrev={() => setViewMonth(prevMonthStr(viewMonth))}
        onNext={() => setViewMonth(nextMonthStr(viewMonth))}
        canGoNext={viewMonth < currentMonth}
        participants={myView}
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

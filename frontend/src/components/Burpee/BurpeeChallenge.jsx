import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

// ─── Constants ────────────────────────────────────────────────────────────────

const PARTICIPANTS = ['Ivan', 'Yurii'];
const P_COLORS = { Ivan: '#6366f1', Yurii: '#10b981' };
const LS_KEY = 'burpee-me';

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
  return apiBurpee('GET', '/v1/burpee', null, token);
}

function logBurpeeEntry(token, { participant, entryDate, reps }) {
  return apiBurpee('POST', '/v1/burpee', { participant, entry_date: entryDate, reps }, token);
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
function fmtMonth(ym) {
  const [y, m] = ym.split('-');
  return new Date(+y, +m - 1).toLocaleString('en', { month: 'long', year: 'numeric' });
}
function fmtMonthShort(ym) {
  const [y, m] = ym.split('-');
  return new Date(+y, +m - 1).toLocaleString('en', { month: 'short' });
}
function fmtDayLabel() {
  const d = new Date();
  return d.toLocaleDateString('en', { day: '2-digit', month: 'short' });
}

// ─── Derived stats ────────────────────────────────────────────────────────────

function computeStats(entries, currentMonth) {
  const prev = prevMonthStr(currentMonth);

  const stats = {};
  for (const p of PARTICIPANTS) {
    const thisMonthEntries = entries.filter(
      (e) => e.participant === p && monthOf(e.entryDate) === currentMonth,
    );
    const prevMonthEntries = entries.filter(
      (e) => e.participant === p && monthOf(e.entryDate) === prev,
    );
    const total = thisMonthEntries.reduce((s, e) => s + e.reps, 0);
    const prevTotal = prevMonthEntries.reduce((s, e) => s + e.reps, 0);
    const best = thisMonthEntries.reduce((b, e) => Math.max(b, e.reps), 0);
    stats[p] = {
      total,
      delta: total - prevTotal,
      days: thisMonthEntries.length,
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
        background: 'var(--bg-base, #0f1117)',
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

function ScoreCard({ participant, stats, isLeader, isMe }) {
  const color = P_COLORS[participant];
  const delta = stats.delta;
  const deltaStr = delta >= 0 ? `↑ +${delta}` : `↓ ${delta}`;
  const deltaColor = delta >= 0 ? '#22c55e' : '#ef4444';

  return (
    <div
      style={{
        flex: 1,
        background: 'var(--bg-elevated, #1a1d27)',
        border: `1.5px solid ${isLeader ? color : 'var(--border, #2a2d3a)'}`,
        borderRadius: 'var(--radius-md, 10px)',
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        boxShadow: isLeader ? `0 0 16px ${color}33` : 'none',
        transition: 'box-shadow 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontWeight: 700, fontSize: 15, color }}>{participant}</span>
        {isMe && (
          <span
            style={{
              fontSize: 10,
              background: color,
              color: '#fff',
              borderRadius: 4,
              padding: '1px 5px',
              fontWeight: 600,
              letterSpacing: 0.5,
            }}
          >
            you
          </span>
        )}
      </div>
      <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--text-primary, #fff)', lineHeight: 1.1 }}>
        {stats.total}
      </div>
      <div style={{ fontSize: 12, color: deltaColor, fontWeight: 600 }}>{deltaStr} vs prev month</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted, #888)', marginTop: 2 }}>
        {stats.days} days logged · best {stats.best}
      </div>
    </div>
  );
}

function LeadIndicator({ stats }) {
  const [a, b] = PARTICIPANTS;
  const diff = stats[a].total - stats[b].total;
  if (diff === 0) {
    return (
      <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-secondary, #aaa)', padding: '4px 0' }}>
        🤝 Tied
      </div>
    );
  }
  const leader = diff > 0 ? a : b;
  const margin = Math.abs(diff);
  return (
    <div
      style={{
        textAlign: 'center',
        fontSize: 13,
        fontWeight: 600,
        color: P_COLORS[leader],
        padding: '4px 0',
      }}
    >
      ⚡ {leader} leads by {margin} reps
    </div>
  );
}

function MonthlyWinsRow({ wins }) {
  if (!wins.length) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, overflowX: 'auto', paddingBottom: 4 }}>
      <span style={{ fontSize: 12, color: 'var(--text-muted, #888)', whiteSpace: 'nowrap', flexShrink: 0 }}>
        history:
      </span>
      {wins.map(({ ym, winner }) => (
        <span
          key={ym}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 3,
            background: winner ? `${P_COLORS[winner]}22` : 'var(--bg-elevated, #1a1d27)',
            border: `1px solid ${winner ? P_COLORS[winner] : 'var(--border, #2a2d3a)'}`,
            color: winner ? P_COLORS[winner] : 'var(--text-muted, #888)',
            borderRadius: 20,
            padding: '2px 9px',
            fontSize: 12,
            fontWeight: 600,
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          {fmtMonthShort(ym)} · {winner ? winner[0] : '–'}
        </span>
      ))}
    </div>
  );
}

function BurpeeHorizontalChart({ chartData, label }) {
  if (!chartData.length) return null;
  const rowHeight = 28;
  const height = chartData.length * rowHeight + 24;

  return (
    <div
      style={{
        background: 'var(--bg-elevated, #1a1d27)',
        borderRadius: 'var(--radius-md, 10px)',
        padding: 16,
        marginTop: 12,
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary, #aaa)', marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {PARTICIPANTS.map((p, i) => {
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
  const [me, setMe] = useState(() => localStorage.getItem(LS_KEY));
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [repsInput, setRepsInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const currentMonth = monthOf(today());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBurpeeEntries(token);
      setEntries(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  // Pre-fill input with today's existing entry for me
  const myTodayEntry = me
    ? entries.find((e) => e.participant === me && e.entryDate === today())
    : null;

  useEffect(() => {
    if (myTodayEntry) {
      setRepsInput(String(myTodayEntry.reps));
    } else {
      setRepsInput('');
    }
  }, [myTodayEntry?.id]);

  function handlePick(name) {
    localStorage.setItem(LS_KEY, name);
    setMe(name);
  }

  function handleSwitch() {
    localStorage.removeItem(LS_KEY);
    setMe(null);
  }

  async function handleLog(e) {
    e.preventDefault();
    const reps = parseInt(repsInput, 10);
    if (!reps || reps < 1 || reps > 300) return;
    setSaving(true);
    setSaveError(null);
    try {
      // If there's an existing entry today for me, delete it first
      if (myTodayEntry) {
        await deleteBurpeeEntry(token, myTodayEntry.id);
      }
      await logBurpeeEntry(token, { participant: me, entryDate: today(), reps });
      await load();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!myTodayEntry) return;
    setSaving(true);
    setSaveError(null);
    try {
      await deleteBurpeeEntry(token, myTodayEntry.id);
      setRepsInput('');
      await load();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Identity screen
  if (!me) {
    return <IdentityPicker onPick={handlePick} />;
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

  const stats = computeStats(entries, currentMonth);
  const wins = computeMonthlyWins(entries);
  const chartData = buildChartData(entries, currentMonth);
  const [a, b] = PARTICIPANTS;
  const leaderName = stats[a].total > stats[b].total ? a : stats[b].total > stats[a].total ? b : null;

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
        <button
          onClick={handleSwitch}
          style={{
            background: 'transparent',
            border: '1px solid var(--border, #2a2d3a)',
            borderRadius: 'var(--radius-md, 8px)',
            color: 'var(--text-secondary, #aaa)',
            fontSize: 12,
            padding: '4px 10px',
            cursor: 'pointer',
          }}
        >
          Switch
        </button>
      </div>

      {/* Scoreboard */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
        {PARTICIPANTS.map((p) => (
          <ScoreCard
            key={p}
            participant={p}
            stats={stats[p]}
            isLeader={leaderName === p}
            isMe={p === me}
          />
        ))}
      </div>
      <LeadIndicator stats={stats} />

      {/* Monthly wins */}
      <MonthlyWinsRow wins={wins} />

      {/* Horizontal chart */}
      <BurpeeHorizontalChart chartData={chartData} label={fmtMonth(currentMonth)} />

      {/* Log form */}
      <div
        style={{
          background: 'var(--bg-elevated, #1a1d27)',
          border: '1px solid var(--border, #2a2d3a)',
          borderRadius: 'var(--radius-md, 10px)',
          padding: '14px 16px',
          marginTop: 12,
        }}
      >
        <div style={{ fontSize: 13, color: 'var(--text-secondary, #aaa)', marginBottom: 10 }}>
          Today, {fmtDayLabel()}
        </div>
        <form onSubmit={handleLog} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input
            type="number"
            min={1}
            max={300}
            placeholder="reps"
            value={repsInput}
            onChange={(e) => setRepsInput(e.target.value)}
            style={{
              width: 80,
              padding: '7px 10px',
              borderRadius: 'var(--radius-md, 8px)',
              border: '1px solid var(--border, #2a2d3a)',
              background: 'var(--bg-base, #0f1117)',
              color: 'var(--text-primary, #fff)',
              fontSize: 14,
              outline: 'none',
            }}
          />
          <button
            type="submit"
            disabled={saving}
            style={{
              background: meColor,
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md, 8px)',
              padding: '7px 16px',
              fontSize: 13,
              fontWeight: 600,
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {myTodayEntry ? `Update for ${me}` : `Log for ${me}`}
          </button>
          {myTodayEntry && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={saving}
              title="Delete today's entry"
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

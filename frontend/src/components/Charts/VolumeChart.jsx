import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatVolume(v) {
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v);
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="tooltip-date">{formatDate(d.date)}</div>
      <div className="tooltip-row">
        <span>Volume</span>
        <strong>{d.volume.toLocaleString()} kg·reps</strong>
      </div>
    </div>
  );
}

export default function VolumeChart({ sessions, metricsMap }) {
  const data = sessions
    .map(s => {
      const m = metricsMap[s.sessionId];
      if (!m) return null;
      return {
        date: s.sessionDate,
        volume: m.benchVolumeKgReps,
      };
    })
    .filter(Boolean)
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  const hasData = data.length > 0;

  return (
    <div className="chart-wrapper">
      <div className="card-title">Bench Volume (kg·reps)</div>
      {hasData ? (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatVolume}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(129,140,248,0.08)' }} />
            <Bar dataKey="volume" fill="#818cf8" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="chart-empty">No volume data for this phase</div>
      )}
    </div>
  );
}

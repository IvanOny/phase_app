import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

function formatDate(dateStr) {
  if (!dateStr) return '';
  const [, mm, dd] = dateStr.split('T')[0].split('-');
  return `${dd}.${mm}`;
}

export default function E1rmChart({ sessions, metricsMap }) {
  const colors = useChartColors();

  function readinessColor(r) {
    if (r == null) return colors.readyNone;
    if (r >= 7)   return colors.readyGreen;
    if (r >= 5)   return colors.readyYellow;
    return colors.readyRed;
  }

  function ReadinessDot(props) {
    const { cx, cy, payload } = props;
    const fill = readinessColor(payload.eliteHrvReadiness);
    return (
      <circle
        cx={cx}
        cy={cy}
        r={5}
        fill={fill}
        stroke={colors.bgApp}
        strokeWidth={1.5}
      />
    );
  }

  function CustomTooltip({ active, payload }) {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="chart-tooltip">
        <div className="tooltip-date">{formatDate(d.date)}</div>
        <div className="tooltip-row">
          <span>e1RM</span>
          <strong>{d.e1rmKg} kg</strong>
        </div>
        <div className="tooltip-row">
          <span>Top set</span>
          <strong>{d.topSetLoadKg} kg × {d.topSetReps}</strong>
        </div>
        {d.eliteHrvReadiness != null && (
          <div className="tooltip-row">
            <span>Readiness</span>
            <strong style={{ color: readinessColor(d.eliteHrvReadiness) }}>
              {d.eliteHrvReadiness}
            </strong>
          </div>
        )}
      </div>
    );
  }

  const data = sessions
    .map(s => {
      const m = metricsMap[s.sessionId];
      if (!m) return null;
      return {
        date: s.sessionDate,
        e1rmKg: m.topSetE1rmKg,
        topSetLoadKg: m.topSetLoadKg,
        topSetReps: m.topSetReps,
        eliteHrvReadiness: s.eliteHrvReadiness,
      };
    })
    .filter(Boolean)
    .sort((a, b) => new Date(a.date) - new Date(b.date));

  const hasData = data.length > 0;

  return (
    <div className="chart-wrapper">
      <div className="card-title">Heavy Strength — e1RM (kg)</div>
      {hasData ? (
        <>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fill: colors.textMuted, fontSize: 12 }}
                axisLine={{ stroke: colors.border }}
                tickLine={false}
              />
              <YAxis
                domain={['dataMin - 5', 'dataMax + 5']}
                tickFormatter={v => `${v}`}
                tick={{ fill: colors.textMuted, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="e1rmKg"
                stroke={colors.accent}
                strokeWidth={2}
                dot={<ReadinessDot />}
                activeDot={{ r: 7, fill: colors.accent }}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="readiness-legend">
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyGreen }} />Ready (≥7)</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyYellow }} />Moderate (5–7)</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyRed }} />Low (&lt;5)</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyNone }} />No data</span>
          </div>
        </>
      ) : (
        <div className="chart-empty">No strength data for this phase</div>
      )}
    </div>
  );
}

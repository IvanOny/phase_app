import { useState, useRef, useEffect } from 'react';
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

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(pointer: coarse)').matches);
  useEffect(() => {
    const mq = window.matchMedia('(pointer: coarse)');
    const handler = e => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return isMobile;
}

export default function E1rmChart({ sessions, metricsMap }) {
  const colors = useChartColors();
  const isMobile = useIsMobile();
  const [showInfo, setShowInfo] = useState(false);
  const [selectedDot, setSelectedDot] = useState(null);
  const infoRef = useRef(null);

  useEffect(() => {
    function handle(e) {
      if (infoRef.current && !infoRef.current.contains(e.target)) setShowInfo(false);
    }
    if (showInfo) document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [showInfo]);

  function readinessColor(r) {
    if (r == null) return colors.readyNone;
    if (r >= 7)   return colors.readyGreen;
    if (r >= 4)   return colors.readyYellow;
    return colors.readyRed;
  }

  function readinessDotProps(val) {
    if (val == null) return { r: 5, opacity: 1 };
    if (val >= 7) {
      const step = val - 7;
      return { r: 7 + step * 3, opacity: Math.max(0.2, 0.85 - step * 0.18) };
    }
    const step = 7 - val;
    return { r: 5 + step * 3, opacity: Math.max(0.15, 0.85 - step * 0.15) };
  }

  function ReadinessDot(props) {
    const { cx, cy, payload } = props;
    const val = payload.eliteHrvReadiness;
    const fill = readinessColor(val);
    const { r, opacity } = readinessDotProps(val);
    return (
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={fill}
        fillOpacity={opacity}
        stroke={colors.bgApp}
        strokeWidth={1.5}
        style={{ cursor: isMobile ? 'pointer' : 'default' }}
        onClick={() => {
          if (!isMobile) return;
          setSelectedDot(prev => prev?.date === payload.date ? null : payload);
        }}
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
      <div className="chart-title-row">
        <span className="card-title">e1RM (kg)</span>
        <div className="info-btn-wrap" ref={infoRef}>
          <button className="info-btn" onClick={() => setShowInfo(v => !v)} aria-label="What is e1RM?">?</button>
          {showInfo && (
            <div className="info-popover">
              <p><strong>Estimated 1-rep max</strong> — a weekly strength snapshot without the risk of true max testing. Each heavy session your top set is used to project peak strength.</p>
              <p className="info-example">Example: 87.5 kg × 5 reps → e1RM <strong>100 kg</strong></p>
            </div>
          )}
        </div>
      </div>
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
              {!isMobile && <Tooltip content={<CustomTooltip />} />}
              <Line
                type="monotone"
                dataKey="e1rmKg"
                stroke={colors.accent}
                strokeWidth={2}
                dot={<ReadinessDot />}
                activeDot={isMobile ? false : { r: 7, fill: colors.accent }}
              />
            </LineChart>
          </ResponsiveContainer>
          {isMobile && selectedDot && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', marginTop: 8, fontSize: 13 }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                {formatDate(selectedDot.date)} · e1RM <strong style={{ color: 'var(--text-primary)' }}>{selectedDot.e1rmKg} kg</strong>
                {selectedDot.eliteHrvReadiness != null && (
                  <> · Readiness <strong style={{ color: readinessColor(selectedDot.eliteHrvReadiness) }}>{selectedDot.eliteHrvReadiness}</strong></>
                )}
              </span>
              <button onClick={() => setSelectedDot(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 13, padding: '0 0 0 8px' }}>✕</button>
            </div>
          )}
          <div className="readiness-legend">
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyGreen }} />Ready (≥7)</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyYellow }} />Moderate (4–6)</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyRed }} />Low (&lt;4)</span>
            <span className="legend-item"><span className="legend-dot" style={{ background: colors.readyNone }} />No data</span>
          </div>
        </>
      ) : (
        <div className="chart-empty">No strength data for this phase</div>
      )}
    </div>
  );
}

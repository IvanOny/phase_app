import { useState, useEffect, useMemo } from 'react';
import { useTooltip } from '../../hooks/useExpandable.js';
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

const BENCH_TYPES = ['heavy', 'volume', 'speed'];

const BENCH_TYPE_MAP = {
  heavy:  'heavy_bench',
  volume: 'volume_bench',
  speed:  'speed_bench',
};

function normDate(d) {
  if (!d) return '';
  return String(d).split('T')[0];
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const m = String(dateStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return String(dateStr);
  return `${m[3]}.${m[2]}`;
}

function formatVolume(v) {
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v);
}

export default function VolumeChart({ sessions, exerciseVolumes, exercises }) {
  const colors = useChartColors();
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);
  const [benchFilters, setBenchFilters] = useState(BENCH_TYPES);
  const [tooltip, openTooltip, chartRef] = useTooltip('chart-volume');
  const [hoveredDate, setHoveredDate] = useState(null);

  useEffect(() => {
    if (exerciseVolumes.length > 0 && selectedExerciseId === null) {
      setSelectedExerciseId(exerciseVolumes[0].exerciseId);
    } else if (exerciseVolumes.length > 0 && !exerciseVolumes.find(e => e.exerciseId === selectedExerciseId)) {
      setSelectedExerciseId(exerciseVolumes[0].exerciseId);
    } else if (exerciseVolumes.length === 0) {
      setSelectedExerciseId(null);
    }
  }, [exerciseVolumes]);

  useEffect(() => {
    setBenchFilters(BENCH_TYPES);
    openTooltip(null);
  }, [selectedExerciseId]);

  const selectedExercise = exerciseVolumes.find(e => e.exerciseId === selectedExerciseId);
  const exerciseInfo = exercises?.find(e => e.exerciseId === selectedExerciseId);
  const isBenchPress = exerciseInfo?.isBarbellBenchPress === true;

  const sessionTypeByDate = useMemo(() => {
    const map = {};
    (sessions ?? []).forEach(s => {
      const key = normDate(s.sessionDate);
      if (key) map[key] = s.sessionType;
    });
    return map;
  }, [sessions]);

  function toggleBenchFilter(type) {
    if (type === 'all') {
      setBenchFilters(allBenchSelected ? [] : BENCH_TYPES);
    } else if (allBenchSelected) {
      // Solo-select: keep only this type
      setBenchFilters([type]);
    } else {
      setBenchFilters(prev =>
        prev.includes(type) ? prev.filter(f => f !== type) : [...prev, type]
      );
    }
  }

  const isBodyweight = exerciseInfo?.isBodyweight === true;
  const allBenchSelected = BENCH_TYPES.every(t => benchFilters.includes(t));

  const data = (selectedExercise?.sessions ?? [])
    .sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate))
    .map(s => {
      const dateKey = normDate(s.sessionDate);
      const sets = s.sets ?? [];
      const totalReps = sets.reduce((sum, set) => sum + set.reps, 0);
      return {
        date: s.sessionDate,
        volume: isBodyweight ? totalReps : s.volumeKgReps,
        topLoadKg: isBodyweight ? null : (s.topLoadKg ?? null),
        sets,
        sessionType: sessionTypeByDate[dateKey] ?? null,
      };
    })
    .filter(s => {
      if (!isBenchPress) return true;
      if (allBenchSelected) return true;
      return benchFilters.some(f => BENCH_TYPE_MAP[f] === s.sessionType);
    });

  const hasData = data.length > 0;
  const unit = isBodyweight ? 'reps' : 'kg·reps';
  const title = selectedExercise
    ? `Volume — ${selectedExercise.exerciseName} (${unit})`
    : `Volume (${unit})`;

  function handleBarClick(barData, _index, event) {
    if (!chartRef.current) return;
    const rect = chartRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    openTooltip(tooltip?.data.date === barData.date ? null : { x, y, data: barData });
  }

  return (
    <div className="chart-wrapper">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div className="card-title" style={{ marginBottom: 0 }}>{title}</div>
        {exerciseVolumes.length > 0 && (
          <select
            value={selectedExerciseId ?? ''}
            onChange={e => setSelectedExerciseId(Number(e.target.value))}
            className="inline-input"
            style={{ fontSize: 12, padding: '2px 6px' }}
          >
            {exerciseVolumes.map(ex => (
              <option key={ex.exerciseId} value={ex.exerciseId}>{ex.exerciseName}</option>
            ))}
          </select>
        )}
      </div>
      {isBenchPress && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 8, flexWrap: 'wrap' }}>
          {['all', 'heavy', 'volume', 'speed'].map(type => {
            const isActive = type === 'all'
              ? allBenchSelected
              : benchFilters.includes(type);
            return (
              <button
                key={type}
                className={`filter-chip${isActive ? ' active' : ''}`}
                onClick={() => toggleBenchFilter(type)}
                style={{ fontSize: 11, padding: '1px 8px' }}
              >
                {type}
              </button>
            );
          })}
        </div>
      )}
      {hasData ? (
        <div ref={chartRef} style={{ position: 'relative' }}>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={data} margin={{ top: 20, right: 16, bottom: 24, left: 0 }} barSize={24} tabIndex={-1}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fill: colors.textMuted, fontSize: 12 }}
                axisLine={{ stroke: colors.border }}
                tickLine={false}
              />
              <YAxis
                tickFormatter={formatVolume}
                tick={{ fill: colors.textMuted, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Bar
                dataKey="volume"
                radius={[3, 3, 0, 0]}
                onClick={handleBarClick}
                onMouseEnter={(data) => setHoveredDate(data.date)}
                onMouseLeave={() => setHoveredDate(null)}
                style={{ cursor: 'pointer' }}
              >
                {data.map((entry, i) => {
                  const isActive = tooltip?.data.date === entry.date;
                  const isHovered = hoveredDate === entry.date;
                  const hasAny = tooltip != null;
                  return <Cell key={i} fill={colors.accent} fillOpacity={isActive ? 1 : hasAny ? 0.35 : isHovered ? 0.75 : 1} />;
                })}
                <LabelList
                  dataKey="topLoadKg"
                  position="top"
                  formatter={v => (v ? `${v}kg` : '')}
                  style={{ fontSize: 10, fill: colors.textMuted }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {tooltip && (
            <div
              className="chart-tooltip"
              style={{
                position: 'absolute',
                left: tooltip.x,
                top: tooltip.y,
                transform: 'translate(-50%, -110%)',
                width: 'fit-content',
                minWidth: 0,
                cursor: 'pointer',
                zIndex: 10,
              }}
              onClick={() => openTooltip(null)}
            >
              {tooltip.data.sets.map((s, i) => (
                <div key={i}>{isBodyweight ? `${s.reps} reps` : `${s.loadKg}×${s.reps}`}</div>
              ))}
              <div style={{ marginTop: 4, borderTop: '1px solid var(--border)', paddingTop: 4 }}>
                <div>Total</div>
                <strong>{tooltip.data.volume.toLocaleString()}</strong>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{unit}</div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="chart-empty">
          {exerciseVolumes.length === 0
            ? 'No volume data for this phase'
            : 'No sessions for selected exercise'}
        </div>
      )}
    </div>
  );
}

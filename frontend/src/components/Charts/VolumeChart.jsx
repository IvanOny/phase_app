import { useState, useEffect, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
  ResponsiveContainer,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

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

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const sets = d.sets ?? [];
  return (
    <div className="chart-tooltip">
      {sets.map((s, i) => (
        <div key={i} className="tooltip-row">
          <span>{s.loadKg}×{s.reps}</span>
        </div>
      ))}
      <div className="tooltip-row" style={{ marginTop: 4, borderTop: '1px solid var(--border)', paddingTop: 4 }}>
        <span>Total</span>
        <strong>{d.volume.toLocaleString()} kg·reps</strong>
      </div>
    </div>
  );
}

export default function VolumeChart({ sessions, exerciseVolumes, exercises }) {
  const colors = useChartColors();
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);
  const [benchFilters, setBenchFilters] = useState(['all']);

  useEffect(() => {
    if (exerciseVolumes.length > 0 && selectedExerciseId === null) {
      setSelectedExerciseId(exerciseVolumes[0].exerciseId);
    } else if (exerciseVolumes.length > 0 && !exerciseVolumes.find(e => e.exerciseId === selectedExerciseId)) {
      setSelectedExerciseId(exerciseVolumes[0].exerciseId);
    } else if (exerciseVolumes.length === 0) {
      setSelectedExerciseId(null);
    }
  }, [exerciseVolumes]);

  // Reset bench filter when exercise changes
  useEffect(() => {
    setBenchFilters(['all']);
  }, [selectedExerciseId]);

  const selectedExercise = exerciseVolumes.find(e => e.exerciseId === selectedExerciseId);
  const exerciseInfo = exercises?.find(e => e.exerciseId === selectedExerciseId);
  const isBenchPress = exerciseInfo?.isBarbellBenchPress === true;

  // date → sessionType map for filtering by bench type
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
      setBenchFilters(['all']);
    } else {
      setBenchFilters(prev => {
        const withoutAll = prev.filter(f => f !== 'all');
        const hasType = withoutAll.includes(type);
        const next = hasType ? withoutAll.filter(f => f !== type) : [...withoutAll, type];
        return next.length === 0 ? ['all'] : next;
      });
    }
  }

  const data = (selectedExercise?.sessions ?? [])
    .sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate))
    .map(s => {
      const dateKey = normDate(s.sessionDate);
      return {
        date: s.sessionDate,
        volume: s.volumeKgReps,
        topLoadKg: s.topLoadKg ?? null,
        sets: s.sets ?? [],
        sessionType: sessionTypeByDate[dateKey] ?? null,
      };
    })
    .filter(s => {
      if (!isBenchPress) return true;
      if (benchFilters.includes('all')) return true;
      return benchFilters.some(f => BENCH_TYPE_MAP[f] === s.sessionType);
    });

  const hasData = data.length > 0;
  const title = selectedExercise
    ? `Volume — ${selectedExercise.exerciseName} (kg·reps)`
    : 'Volume (kg·reps)';

  const allBenchSelected = ['heavy', 'volume', 'speed'].every(t => benchFilters.includes(t));

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
              ? benchFilters.includes('all') || allBenchSelected
              : benchFilters.includes(type) && !benchFilters.includes('all');
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
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 20, right: 16, bottom: 24, left: 0 }} barSize={24}>
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
            <Tooltip content={<CustomTooltip />} cursor={{ fill: colors.accentTint }} />
            <Bar dataKey="volume" fill={colors.accent} radius={[3, 3, 0, 0]}>
              <LabelList
                dataKey="topLoadKg"
                position="top"
                formatter={v => (v ? `${v}kg` : '')}
                style={{ fontSize: 10, fill: colors.textMuted }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
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

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useChartColors } from '../../hooks/useChartColors.js';

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

export default function VolumeChart({ sessions, exerciseVolumes }) {
  const colors = useChartColors();
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);

  useEffect(() => {
    if (exerciseVolumes.length > 0 && selectedExerciseId === null) {
      setSelectedExerciseId(exerciseVolumes[0].exerciseId);
    } else if (exerciseVolumes.length > 0 && !exerciseVolumes.find(e => e.exerciseId === selectedExerciseId)) {
      setSelectedExerciseId(exerciseVolumes[0].exerciseId);
    } else if (exerciseVolumes.length === 0) {
      setSelectedExerciseId(null);
    }
  }, [exerciseVolumes]);

  const volumeBenchIds = new Set(
    sessions.filter(s => s.sessionType === 'volume_bench').map(s => s.sessionId)
  );

  const selectedExercise = exerciseVolumes.find(e => e.exerciseId === selectedExerciseId);

  const data = (selectedExercise?.sessions ?? [])
    .filter(s => volumeBenchIds.has(s.sessionId))
    .sort((a, b) => new Date(a.sessionDate) - new Date(b.sessionDate))
    .map(s => ({ date: s.sessionDate, volume: s.volumeKgReps }));

  const hasData = data.length > 0;
  const title = selectedExercise
    ? `Volume bench — ${selectedExercise.exerciseName} (kg·reps)`
    : 'Volume bench (kg·reps)';

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
      {hasData ? (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
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
            <Bar dataKey="volume" fill={colors.accent} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="chart-empty">
          {exerciseVolumes.length === 0
            ? 'No volume data for this phase'
            : 'No volume bench sessions for selected exercise'}
        </div>
      )}
    </div>
  );
}

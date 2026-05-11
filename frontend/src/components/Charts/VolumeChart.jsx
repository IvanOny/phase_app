import { useState, useEffect, useMemo } from 'react';
import { useTooltip, useIsTouchDevice } from '../../hooks/useExpandable.js';
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
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
  const isTouch = useIsTouchDevice();
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);
  const [benchFilters, setBenchFilters] = useState(['volume']);
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
    setBenchFilters(['volume']);
    openTooltip(null);
  }, [selectedExerciseId]);

  const sessionTypeByDate = useMemo(() => {
    const map = {};
    (sessions ?? []).forEach(s => {
      const key = normDate(s.sessionDate);
      if (key) map[key] = s.sessionType;
    });
    return map;
  }, [sessions]);

  const selectedExercise = exerciseVolumes.find(e => e.exerciseId === selectedExerciseId);
  const exerciseInfo = exercises?.find(e => e.exerciseId === selectedExerciseId);
  const isBenchPress = exerciseInfo?.isBarbellBenchPress === true;

  function selectBenchFilter(type) {
    setBenchFilters([type]);
  }

  const isBodyweight = exerciseInfo?.isBodyweight === true;

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
      return benchFilters.some(f => BENCH_TYPE_MAP[f] === s.sessionType);
    });

  const hasData = data.length > 0;
  const unit = isBodyweight ? 'reps' : 'kg·reps';
  const title = selectedExercise
    ? `Volume — ${selectedExercise.exerciseName}`
    : 'Volume';

  function getTooltipPos(event) {
    if (!chartRef.current || !event) return null;
    const rect = chartRef.current.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function makeHandler(type) {
    const isActive = (barData) => tooltip?.data.date === barData.date && tooltip?.type === type;
    return {
      onClick(barData, _i, event) {
        if (!isTouch) return;
        const pos = getTooltipPos(event);
        if (!pos) return;
        openTooltip(isActive(barData) ? null : { ...pos, data: barData, type });
      },
      onMouseEnter(barData, _i, event) {
        setHoveredDate(barData.date);
        if (isTouch) return;
        const pos = getTooltipPos(event);
        if (!pos) return;
        openTooltip({ ...pos, data: barData, type });
      },
      onMouseLeave() {
        setHoveredDate(null);
        if (!isTouch) openTooltip(null);
      },
    };
  }

  const volumeHandlers = makeHandler('volume');
  const loadHandlers   = makeHandler('load');

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
          {BENCH_TYPES.map(type => (
            <button
              key={type}
              className={`filter-chip${benchFilters.includes(type) ? ' active' : ''}`}
              onClick={() => selectBenchFilter(type)}
              style={{ fontSize: 11, padding: '1px 8px' }}
            >
              {type}
            </button>
          ))}
        </div>
      )}
      {hasData ? (
        <div
          ref={chartRef}
          style={{ position: 'relative' }}
          onMouseLeave={() => { if (!isTouch) { setHoveredDate(null); openTooltip(null); } }}
        >
          {!isBodyweight && (
            <div style={{ display: 'flex', gap: 12, marginBottom: 6, fontSize: 11, color: colors.textMuted }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: colors.accent, display: 'inline-block' }} />
                volume ({unit})
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: colors.readyGreen, display: 'inline-block' }} />
                top load (kg)
              </span>
            </div>
          )}
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              data={data}
              margin={{ top: 8, right: 40, bottom: 24, left: 0 }}
              barSize={14}
              barCategoryGap="30%"
              tabIndex={-1}
              onMouseLeave={() => { if (!isTouch) { setHoveredDate(null); openTooltip(null); } }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fill: colors.textMuted, fontSize: 12 }}
                axisLine={{ stroke: colors.border }}
                tickLine={false}
              />
              <YAxis
                yAxisId="left"
                tickFormatter={formatVolume}
                tick={{ fill: colors.textMuted, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              {!isBodyweight && (
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tickFormatter={v => `${v}`}
                  tick={{ fill: colors.readyGreen, fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={36}
                />
              )}
              <Bar
                yAxisId="left"
                dataKey="volume"
                radius={[3, 3, 0, 0]}
                onClick={volumeHandlers.onClick}
                onMouseEnter={volumeHandlers.onMouseEnter}
                onMouseLeave={volumeHandlers.onMouseLeave}
                style={{ cursor: 'pointer' }}
              >
                {data.map((entry, i) => {
                  const isActive = tooltip?.data.date === entry.date && tooltip?.type === 'volume';
                  const isHovered = hoveredDate === entry.date;
                  const hasAny = tooltip != null;
                  return <Cell key={i} fill={colors.accent} fillOpacity={isActive ? 1 : hasAny ? 0.35 : isHovered ? 0.75 : 1} />;
                })}
              </Bar>
              {!isBodyweight && (
                <Bar
                  yAxisId="right"
                  dataKey="topLoadKg"
                  radius={[3, 3, 0, 0]}
                  onClick={loadHandlers.onClick}
                  onMouseEnter={loadHandlers.onMouseEnter}
                  onMouseLeave={loadHandlers.onMouseLeave}
                  style={{ cursor: 'pointer' }}
                >
                  {data.map((entry, i) => {
                    const isActive = tooltip?.data.date === entry.date && tooltip?.type === 'load';
                    const isHovered = hoveredDate === entry.date;
                    const hasAny = tooltip != null;
                    return <Cell key={i} fill={colors.readyGreen} fillOpacity={isActive ? 1 : hasAny ? 0.3 : isHovered ? 0.9 : 0.75} />;
                  })}
                </Bar>
              )}
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
                zIndex: 10,
                pointerEvents: isTouch ? 'auto' : 'none',
                cursor: isTouch ? 'pointer' : 'default',
              }}
              onClick={isTouch ? () => openTooltip(null) : undefined}
            >
              {tooltip.type === 'load' ? (
                <>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>top load</div>
                  <strong>{tooltip.data.topLoadKg} kg</strong>
                </>
              ) : (
                <>
                  {tooltip.data.sets.map((s, i) => (
                    <div key={i}>{isBodyweight ? `${s.reps} reps` : `${s.loadKg}×${s.reps}`}</div>
                  ))}
                  <div style={{ marginTop: 4, borderTop: '1px solid var(--border)', paddingTop: 4 }}>
                    <strong>{tooltip.data.volume.toLocaleString()}</strong>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{unit}</div>
                  </div>
                </>
              )}
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

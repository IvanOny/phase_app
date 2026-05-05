export const MOCK_PHASES = [
  {
    phaseId: 1,
    phaseType: 'bench',
    startDate: '2026-01-01',
    endDate: '2026-03-31',
    name: 'Q1 Bench Focus',
  },
  {
    phaseId: 2,
    phaseType: 'pull_ups',
    startDate: '2026-04-01',
    endDate: '2026-06-30',
    name: 'Apr Pull-ups Block',
  },
];

export const MOCK_SESSIONS = [
  { sessionId: 101, phaseId: 1, sessionDate: '2026-01-08', sessionType: 'heavy_bench',  eliteHrvReadiness: 8.1, garminOvernightHrv: 62.0 },
  { sessionId: 107, phaseId: 1, sessionDate: '2026-01-15', sessionType: 'volume_bench', eliteHrvReadiness: 7.5, garminOvernightHrv: 60.0 },
  { sessionId: 102, phaseId: 1, sessionDate: '2026-01-22', sessionType: 'heavy_bench',  eliteHrvReadiness: 6.3, garminOvernightHrv: 54.5 },
  { sessionId: 108, phaseId: 1, sessionDate: '2026-01-29', sessionType: 'volume_bench', eliteHrvReadiness: 7.0, garminOvernightHrv: 58.0 },
  { sessionId: 103, phaseId: 1, sessionDate: '2026-02-05', sessionType: 'heavy_bench',  eliteHrvReadiness: 7.8, garminOvernightHrv: 60.2 },
  { sessionId: 109, phaseId: 1, sessionDate: '2026-02-12', sessionType: 'volume_bench', eliteHrvReadiness: 8.0, garminOvernightHrv: 63.0 },
  { sessionId: 104, phaseId: 1, sessionDate: '2026-02-19', sessionType: 'heavy_bench',  eliteHrvReadiness: 4.5, garminOvernightHrv: 48.1 },
  { sessionId: 110, phaseId: 1, sessionDate: '2026-02-26', sessionType: 'volume_bench', eliteHrvReadiness: 6.5, garminOvernightHrv: 55.0 },
  { sessionId: 105, phaseId: 1, sessionDate: '2026-03-05', sessionType: 'heavy_bench',  eliteHrvReadiness: 7.2, garminOvernightHrv: 58.7 },
  { sessionId: 111, phaseId: 1, sessionDate: '2026-03-12', sessionType: 'volume_bench', eliteHrvReadiness: 7.8, garminOvernightHrv: 61.0 },
  { sessionId: 106, phaseId: 1, sessionDate: '2026-03-19', sessionType: 'heavy_bench',  eliteHrvReadiness: 8.5, garminOvernightHrv: 65.3 },
  { sessionId: 201, phaseId: 2, sessionDate: '2026-04-07', sessionType: 'pull',         eliteHrvReadiness: 7.0, garminOvernightHrv: 57.4 },
  { sessionId: 202, phaseId: 2, sessionDate: '2026-04-21', sessionType: 'pull',         eliteHrvReadiness: 6.8, garminOvernightHrv: 55.9 },
];

export const MOCK_E1RM_METRICS = {
  101: { sessionId: 101, sessionDate: '2026-01-08', topSetE1rmKg: 100.0, topSetReps: 5,  topSetLoadKg: 87.5  },
  102: { sessionId: 102, sessionDate: '2026-01-22', topSetE1rmKg: 102.5, topSetReps: 5,  topSetLoadKg: 90.0  },
  103: { sessionId: 103, sessionDate: '2026-02-05', topSetE1rmKg: 105.0, topSetReps: 4,  topSetLoadKg: 91.0  },
  104: { sessionId: 104, sessionDate: '2026-02-19', topSetE1rmKg: 104.0, topSetReps: 3,  topSetLoadKg: 94.0  },
  105: { sessionId: 105, sessionDate: '2026-03-05', topSetE1rmKg: 108.5, topSetReps: 4,  topSetLoadKg: 95.0  },
  106: { sessionId: 106, sessionDate: '2026-03-19', topSetE1rmKg: 112.0, topSetReps: 5,  topSetLoadKg: 100.0 },
};

export const MOCK_VOLUME_METRICS = {
  101: { sessionId: 101, sessionDate: '2026-01-08', benchVolumeKgReps: 2450 },
  102: { sessionId: 102, sessionDate: '2026-01-22', benchVolumeKgReps: 2700 },
  103: { sessionId: 103, sessionDate: '2026-02-05', benchVolumeKgReps: 3100 },
  104: { sessionId: 104, sessionDate: '2026-02-19', benchVolumeKgReps: 2200 },
  105: { sessionId: 105, sessionDate: '2026-03-05', benchVolumeKgReps: 3400 },
  106: { sessionId: 106, sessionDate: '2026-03-19', benchVolumeKgReps: 3800 },
};

export const MOCK_BENCHMARKS = [
  // Pull-ups — bench phase
  { benchmarkId: 10, phaseId: 1, benchmarkDate: '2026-01-15', benchmarkType: 'max_bodyweight_pullups', reps: 18, formStandardVersion: 'v1.0' },
  { benchmarkId: 11, phaseId: 1, benchmarkDate: '2026-02-12', benchmarkType: 'max_bodyweight_pullups', reps: 19, formStandardVersion: 'v1.0' },
  { benchmarkId: 12, phaseId: 1, benchmarkDate: '2026-03-25', benchmarkType: 'max_bodyweight_pullups', reps: 20, formStandardVersion: 'v1.0' },
  // Pull-ups — pull-ups phase
  { benchmarkId: 20, phaseId: 2, benchmarkDate: '2026-04-10', benchmarkType: 'max_bodyweight_pullups', reps: 21, formStandardVersion: 'v1.0' },
  { benchmarkId: 21, phaseId: 2, benchmarkDate: '2026-04-17', benchmarkType: 'max_bodyweight_pullups', reps: 22, formStandardVersion: 'v1.0' },
  { benchmarkId: 22, phaseId: 2, benchmarkDate: '2026-04-24', benchmarkType: 'max_bodyweight_pullups', reps: 23, formStandardVersion: 'v1.0' },
  // Run — bench phase
  { benchmarkId: 13, phaseId: 1, benchmarkDate: '2026-01-20', benchmarkType: 'run_aerobic_test', avgHr: 139, paceMinPerKm: 5.55, targetHr: 140, durationMin: 40, protocolCompliant: true },
  { benchmarkId: 14, phaseId: 1, benchmarkDate: '2026-03-10', benchmarkType: 'run_aerobic_test', avgHr: 138, paceMinPerKm: 5.42, targetHr: 140, durationMin: 40, protocolCompliant: true },
  // Run — pull-ups phase
  { benchmarkId: 23, phaseId: 2, benchmarkDate: '2026-04-05', benchmarkType: 'run_aerobic_test', avgHr: 140, paceMinPerKm: 5.38, targetHr: 140, durationMin: 40, protocolCompliant: true },
  { benchmarkId: 24, phaseId: 2, benchmarkDate: '2026-04-22', benchmarkType: 'run_aerobic_test', avgHr: 137, paceMinPerKm: 5.25, targetHr: 140, durationMin: 40, protocolCompliant: true },
];

export const MOCK_EXERCISES = [
  { exerciseId: 1, exerciseName: 'Barbell Bench Press', isBarbellBenchPress: true },
  { exerciseId: 2, exerciseName: 'Pull-up',             isBarbellBenchPress: false },
  { exerciseId: 3, exerciseName: 'Incline DB Press',    isBarbellBenchPress: false },
  { exerciseId: 4, exerciseName: 'Dip',                 isBarbellBenchPress: false },
];

// Exercise volumes by phase — exerciseId → { exerciseName, sessions: [{sessionId, sessionDate, volumeKgReps}] }
export const MOCK_EXERCISE_VOLUMES = {
  1: [
    {
      exerciseId: 1,
      exerciseName: 'Barbell Bench Press',
      sessions: [
        { sessionId: 101, sessionDate: '2026-01-08', volumeKgReps: 2450 },
        { sessionId: 107, sessionDate: '2026-01-15', volumeKgReps: 3200 },
        { sessionId: 102, sessionDate: '2026-01-22', volumeKgReps: 2700 },
        { sessionId: 108, sessionDate: '2026-01-29', volumeKgReps: 3400 },
        { sessionId: 103, sessionDate: '2026-02-05', volumeKgReps: 3100 },
        { sessionId: 109, sessionDate: '2026-02-12', volumeKgReps: 3700 },
        { sessionId: 104, sessionDate: '2026-02-19', volumeKgReps: 2200 },
        { sessionId: 110, sessionDate: '2026-02-26', volumeKgReps: 3900 },
        { sessionId: 105, sessionDate: '2026-03-05', volumeKgReps: 3400 },
        { sessionId: 111, sessionDate: '2026-03-12', volumeKgReps: 4100 },
        { sessionId: 106, sessionDate: '2026-03-19', volumeKgReps: 3800 },
      ],
    },
    {
      exerciseId: 3,
      exerciseName: 'Incline DB Press',
      sessions: [
        { sessionId: 107, sessionDate: '2026-01-15', volumeKgReps: 1200 },
        { sessionId: 108, sessionDate: '2026-01-29', volumeKgReps: 1350 },
        { sessionId: 109, sessionDate: '2026-02-12', volumeKgReps: 1500 },
        { sessionId: 110, sessionDate: '2026-02-26', volumeKgReps: 1600 },
        { sessionId: 111, sessionDate: '2026-03-12', volumeKgReps: 1750 },
      ],
    },
    {
      exerciseId: 4,
      exerciseName: 'Dip',
      sessions: [
        { sessionId: 107, sessionDate: '2026-01-15', volumeKgReps: 800 },
        { sessionId: 108, sessionDate: '2026-01-29', volumeKgReps: 900 },
        { sessionId: 109, sessionDate: '2026-02-12', volumeKgReps: 950 },
        { sessionId: 111, sessionDate: '2026-03-12', volumeKgReps: 1050 },
      ],
    },
  ],
  2: [
    {
      exerciseId: 2,
      exerciseName: 'Pull-up',
      sessions: [
        { sessionId: 201, sessionDate: '2026-04-07', volumeKgReps: 560 },
        { sessionId: 202, sessionDate: '2026-04-21', volumeKgReps: 630 },
      ],
    },
  ],
};

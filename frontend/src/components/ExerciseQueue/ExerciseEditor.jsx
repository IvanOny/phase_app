import { useState } from 'react';

const SCHEDULES = [
  { v: 'queue', label: 'Queue (opportunistic)' },
  { v: 'fixed', label: 'Fixed (every N days)' },
  { v: 'acquisition', label: 'Acquisition (learn a move)' },
];
const LOCATIONS = ['home', 'barrack', 'random'];
const LOADS = ['', 'easy', 'upper', 'lower', 'systemic'];
const STATUSES = ['active', 'paused', 'parked'];

export default function ExerciseEditor({ exercise, onSave, onDelete, onClose }) {
  const [f, setF] = useState({
    name: exercise.name ?? '',
    description: exercise.description ?? '',
    scheduleType: exercise.scheduleType ?? 'queue',
    repeatIntervalDays: exercise.repeatIntervalDays ?? '',
    acqIntervalDays: exercise.acqIntervalDays ?? '',
    acqTargetSessions: exercise.acqTargetSessions ?? '',
    focusArea: exercise.focusArea ?? '',
    location: exercise.location ?? 'random',
    equipment: exercise.equipment ?? '',
    loadTag: exercise.loadTag ?? '',
    status: exercise.status ?? 'active',
  });
  const [saving, setSaving] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [err, setErr] = useState(null);
  const set = (k, v) => setF(s => ({ ...s, [k]: v }));

  async function save() {
    if (!f.name.trim()) { setErr('Name is required.'); return; }
    setSaving(true); setErr(null);
    const patch = {
      name: f.name.trim(), description: f.description, scheduleType: f.scheduleType,
      focusArea: f.focusArea, location: f.location, equipment: f.equipment,
      loadTag: f.loadTag, status: f.status,
    };
    if (f.scheduleType === 'fixed') {
      patch.repeatIntervalDays = f.repeatIntervalDays === '' ? null : Number(f.repeatIntervalDays);
    } else if (f.scheduleType === 'acquisition') {
      patch.acqIntervalDays = f.acqIntervalDays === '' ? null : Number(f.acqIntervalDays);
      patch.acqTargetSessions = f.acqTargetSessions === '' ? null : Number(f.acqTargetSessions);
    }
    try { await onSave(exercise.id, patch); onClose(); }
    catch (e) { setErr(e.message); setSaving(false); }
  }

  return (
    <div className="exq-modal-backdrop" onClick={onClose}>
      <div className="exq-modal" onClick={e => e.stopPropagation()}>
        <div className="exq-modal-head">
          <span>Edit exercise</span>
          <button className="exq-btn" onClick={onClose}>✕</button>
        </div>

        <label className="exq-field"><span>Name</span>
          <input value={f.name} onChange={e => set('name', e.target.value)} autoFocus />
        </label>
        <label className="exq-field"><span>Description</span>
          <input value={f.description} onChange={e => set('description', e.target.value)} placeholder="—" />
        </label>

        <label className="exq-field"><span>Schedule</span>
          <select value={f.scheduleType} onChange={e => set('scheduleType', e.target.value)}>
            {SCHEDULES.map(s => <option key={s.v} value={s.v}>{s.label}</option>)}
          </select>
        </label>
        {f.scheduleType === 'fixed' && (
          <label className="exq-field"><span>Every N days</span>
            <input type="number" min="1" value={f.repeatIntervalDays} onChange={e => set('repeatIntervalDays', e.target.value)} />
          </label>
        )}
        {f.scheduleType === 'acquisition' && (
          <>
            <label className="exq-field"><span>Every N days</span>
              <input type="number" min="1" value={f.acqIntervalDays} onChange={e => set('acqIntervalDays', e.target.value)} />
            </label>
            <label className="exq-field"><span>Target sessions</span>
              <input type="number" min="1" value={f.acqTargetSessions} onChange={e => set('acqTargetSessions', e.target.value)} />
            </label>
            <div className="exq-field-note">Progress: {exercise.acqSessionsDone ?? 0}/{exercise.acqTargetSessions ?? '—'}</div>
          </>
        )}

        <label className="exq-field"><span>Focus</span>
          <input value={f.focusArea} onChange={e => set('focusArea', e.target.value)} placeholder="e.g. knee shoulder" />
        </label>
        <div className="exq-field-row">
          <label className="exq-field"><span>Location</span>
            <select value={f.location} onChange={e => set('location', e.target.value)}>
              {LOCATIONS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </label>
          <label className="exq-field"><span>Load</span>
            <select value={f.loadTag} onChange={e => set('loadTag', e.target.value)}>
              {LOADS.map(l => <option key={l} value={l}>{l || '—'}</option>)}
            </select>
          </label>
        </div>
        <label className="exq-field"><span>Equipment</span>
          <input value={f.equipment} onChange={e => set('equipment', e.target.value)} placeholder="e.g. band" />
        </label>
        <label className="exq-field"><span>Status</span>
          <select value={f.status} onChange={e => set('status', e.target.value)}>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>

        {err && <div className="exq-error" style={{ marginTop: 8 }}>{err}</div>}

        <div className="exq-modal-actions">
          {confirmDel ? (
            <>
              <span className="exq-field-note">Delete for good?</span>
              <button className="exq-btn exq-btn--danger" onClick={async () => { await onDelete(exercise.id); onClose(); }}>Delete</button>
              <button className="exq-btn" onClick={() => setConfirmDel(false)}>Keep</button>
            </>
          ) : (
            <>
              <button className="exq-btn exq-btn--danger" onClick={() => setConfirmDel(true)}>Delete</button>
              <span style={{ flex: 1 }} />
              <button className="exq-btn" onClick={onClose}>Cancel</button>
              <button className="exq-btn active" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

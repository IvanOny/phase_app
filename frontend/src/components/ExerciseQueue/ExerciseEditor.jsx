import { useState } from 'react';

// One queue, five tiers. Tier drives how often an item surfaces: an item
// builds "pressure" while it sits undone, at a rate set by its tier, and the
// most pressured one is served next — so these weights are the frequency ratio.
const TIERS = [
  { v: 1, label: 'Tier 1 — most often' },
  { v: 2, label: 'Tier 2 — regular' },
  { v: 3, label: 'Tier 3 — occasional' },
  { v: 4, label: 'Tier 4 — rare' },
  { v: 5, label: 'Tier 5 — hardly ever' },
];
const STATUSES = ['active', 'paused', 'parked'];

export default function ExerciseEditor({ exercise, onSave, onDelete, onClose }) {
  const [f, setF] = useState({
    name: exercise.name ?? '',
    description: exercise.description ?? '',
    tier: exercise.tier ?? 2,
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
      name: f.name.trim(),
      description: f.description,
      tier: Number(f.tier),
      status: f.status,
    };
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

        <label className="exq-field"><span>Name (shown on calendar)</span>
          <input value={f.name} onChange={e => set('name', e.target.value)} autoFocus />
        </label>
        <label className="exq-field"><span>Description (hover tooltip)</span>
          <input value={f.description} onChange={e => set('description', e.target.value)} placeholder="fuller detail, shown on hover" />
        </label>

        <label className="exq-field"><span>Tier</span>
          <select value={f.tier} onChange={e => set('tier', e.target.value)}>
            {TIERS.map(t => <option key={t.v} value={t.v}>{t.label}</option>)}
          </select>
        </label>
        <div className="exq-field-note">Tier 1 comes up about three times as often as tier 3, and twelve times as often as tier 5.</div>

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

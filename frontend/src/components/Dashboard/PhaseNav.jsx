import { useState, useEffect } from 'react';
import ConfirmDialog from '../Common/ConfirmDialog.jsx';

const TYPE_CONFIG = {
  bench:    { label: 'Push', color: 'var(--type-push)' },
  pull_ups: { label: 'Pull', color: 'var(--type-pull)' },
  run:      { label: 'Run',  color: 'var(--type-run)'  },
};

const TYPE_ORDER = ['bench', 'pull_ups', 'run'];

function today() {
  return new Date().toISOString().slice(0, 10);
}

export default function PhaseNav({
  phases,
  selectedPhaseId,
  onSelect,
  onAddPhase,
  onUpdatePhase,
  onDeletePhase,
  isAuthenticated,
}) {
  const activePhase = phases.find(p => p.phaseId === selectedPhaseId);
  const [selectedType, setSelectedType] = useState(activePhase?.phaseType ?? 'bench');
  const [editingId, setEditingId] = useState(null);
  const [confirmPhaseId, setConfirmPhaseId] = useState(null);

  useEffect(() => {
    if (activePhase) setSelectedType(activePhase.phaseType);
  }, [activePhase?.phaseType]);
  const [editFields, setEditFields] = useState({});

  const typedPhases = phases
    .filter(p => p.phaseType === selectedType)
    .sort((a, b) => new Date(b.startDate) - new Date(a.startDate));

  function handleTypeTab(type) {
    setSelectedType(type);
    setEditingId(null);
  }

  function startEdit(phase, e) {
    e.stopPropagation();
    setEditingId(phase.phaseId);
    setEditFields({
      name: phase.name || '',
      startDate: phase.startDate || today(),
      endDate: phase.endDate || '',
    });
  }

  function cancelEdit(e) {
    e?.stopPropagation();
    setEditingId(null);
  }

  async function saveEdit(phaseId, e) {
    e.stopPropagation();
    await onUpdatePhase(phaseId, {
      name: editFields.name || null,
      startDate: editFields.startDate,
      endDate: editFields.endDate || null,
    });
    setEditingId(null);
  }

  function handleDelete(phaseId, e) {
    e.stopPropagation();
    setConfirmPhaseId(phaseId);
  }

  return (
    <div className="phase-nav-container">
      <div className="phase-type-tabs">
        {TYPE_ORDER.map(type => {
          const cfg = TYPE_CONFIG[type];
          const isActive = selectedType === type;
          return (
            <button
              key={type}
              className={`phase-type-tab${isActive ? ' active' : ''}`}
              style={{ '--tab-color': cfg.color }}
              onClick={() => handleTypeTab(type)}
            >
              <span className="phase-type-tab-dot" />
              {cfg.label}
            </button>
          );
        })}
      </div>

      <div className="phase-pills-row">
        {typedPhases.map(phase => {
          const isSelected = phase.phaseId === selectedPhaseId;
          const isEditing = editingId === phase.phaseId;

          if (isEditing) {
            return (
              <div key={phase.phaseId} className="phase-pill phase-pill--editing">
                <input
                  className="pill-edit-input"
                  placeholder="Name"
                  value={editFields.name}
                  onChange={e => setEditFields(f => ({ ...f, name: e.target.value }))}
                  onClick={e => e.stopPropagation()}
                  autoFocus
                />
                <div className="pill-edit-dates">
                  <input
                    type="date"
                    className="pill-edit-input"
                    value={editFields.startDate}
                    onChange={e => setEditFields(f => ({ ...f, startDate: e.target.value }))}
                    onClick={e => e.stopPropagation()}
                  />
                  <span className="pill-edit-dash">–</span>
                  <input
                    type="date"
                    className="pill-edit-input"
                    value={editFields.endDate}
                    onChange={e => setEditFields(f => ({ ...f, endDate: e.target.value }))}
                    onClick={e => e.stopPropagation()}
                  />
                </div>
                <div className="pill-edit-actions">
                  <button className="btn btn-primary btn-xs" onClick={e => saveEdit(phase.phaseId, e)}>Save</button>
                  <button className="btn btn-ghost btn-xs" onClick={cancelEdit}>Cancel</button>
                </div>
              </div>
            );
          }

          return (
            <div
              key={phase.phaseId}
              className={`phase-pill${isSelected ? ' active' : ''}`}
              style={{ '--tab-color': TYPE_CONFIG[selectedType].color }}
              onClick={() => onSelect(phase.phaseId)}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && onSelect(phase.phaseId)}
            >
              <span className="pill-name">{phase.name || '(unnamed)'}</span>
              {isAuthenticated && (
                <span className="pill-actions">
                  <button
                    className="pill-action-btn"
                    title="Edit"
                    onClick={e => startEdit(phase, e)}
                    aria-label="Edit phase"
                  >✎</button>
                  <button
                    className="pill-action-btn pill-action-btn--danger"
                    title="Delete"
                    onClick={e => handleDelete(phase.phaseId, e)}
                    aria-label="Delete phase"
                  >×</button>
                </span>
              )}
            </div>
          );
        })}

        {isAuthenticated && (
          <button
            className="phase-pill-add"
            style={{ '--tab-color': TYPE_CONFIG[selectedType].color }}
            onClick={() => onAddPhase(selectedType)}
            title={`Add ${TYPE_CONFIG[selectedType].label} phase`}
          >
            + Add
          </button>
        )}
      </div>
      {confirmPhaseId && (
        <ConfirmDialog
          message="Delete this phase? This cannot be undone."
          onConfirm={async () => { const id = confirmPhaseId; setConfirmPhaseId(null); await onDeletePhase(id); }}
          onCancel={() => setConfirmPhaseId(null)}
        />
      )}
    </div>
  );
}

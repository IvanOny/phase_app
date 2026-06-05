import { useState, useEffect } from 'react';
import ConfirmDialog from '../Common/ConfirmDialog.jsx';

const TYPE_CONFIG = {
  powerlifting: { label: 'Powerlifting', color: 'var(--type-pl, #a78bfa)' },
  bench:        { label: 'Push', color: 'var(--type-push)' },
  pull_ups:     { label: 'Pull', color: 'var(--type-pull)' },
  run:          { label: 'Run',  color: 'var(--type-run)'  },
};

const TYPE_ORDER = ['powerlifting', 'bench', 'pull_ups', 'run'];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(d) {
  if (!d) return '';
  const m = String(d).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}.${m[2]}.${m[1]}` : String(d);
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
  const [editFields, setEditFields] = useState({});
  const [confirmPhaseId, setConfirmPhaseId] = useState(null);

  useEffect(() => {
    if (activePhase) setSelectedType(activePhase.phaseType);
  }, [activePhase?.phaseType]);

  const typedPhases = phases
    .filter(p => p.phaseType === selectedType)
    .sort((a, b) => new Date(b.startDate) - new Date(a.startDate));

  // Index within current type — sync to selectedPhaseId when type matches
  const selectedIdxInType = typedPhases.findIndex(p => p.phaseId === selectedPhaseId);
  const [tileIdx, setTileIdx] = useState(Math.max(0, selectedIdxInType));

  useEffect(() => {
    const idx = typedPhases.findIndex(p => p.phaseId === selectedPhaseId);
    if (idx >= 0) setTileIdx(idx);
    else setTileIdx(0);
  }, [selectedType, selectedPhaseId, typedPhases.map(p => p.phaseId).join(',')]);

  const safeIdx = Math.min(tileIdx, Math.max(0, typedPhases.length - 1));
  const visiblePhase = typedPhases[safeIdx] ?? null;

  function handleTypeTab(type) {
    setSelectedType(type);
    setEditingId(null);
  }

  function handlePrev() {
    const newIdx = Math.max(0, safeIdx - 1);
    setTileIdx(newIdx);
    if (typedPhases[newIdx]) selectAndScroll(typedPhases[newIdx].phaseId);
  }

  function handleNext() {
    const newIdx = Math.min(typedPhases.length - 1, safeIdx + 1);
    setTileIdx(newIdx);
    if (typedPhases[newIdx]) selectAndScroll(typedPhases[newIdx].phaseId);
  }

  function startEdit(e) {
    e.stopPropagation();
    if (!visiblePhase) return;
    setEditingId(visiblePhase.phaseId);
    setEditFields({
      name: visiblePhase.name || '',
      startDate: visiblePhase.startDate || today(),
      endDate: visiblePhase.endDate || '',
    });
  }

  function cancelEdit(e) {
    e?.stopPropagation();
    setEditingId(null);
  }

  async function saveEdit(e) {
    e.stopPropagation();
    await onUpdatePhase(editingId, {
      name: editFields.name || null,
      startDate: editFields.startDate,
      endDate: editFields.endDate || null,
    });
    setEditingId(null);
  }

  function selectAndScroll(phaseId) {
    onSelect(phaseId);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const tabColor = TYPE_CONFIG[selectedType]?.color ?? 'var(--accent)';
  const isEditing = editingId === visiblePhase?.phaseId;

  return (
    <div className="phase-nav-container">
      <div className="phase-type-tabs">
        <button
          className="phase-nav-arrow"
          style={{ '--tab-color': tabColor }}
          onClick={() => {
            const i = TYPE_ORDER.indexOf(selectedType);
            if (i > 0) handleTypeTab(TYPE_ORDER[i - 1]);
          }}
          disabled={TYPE_ORDER.indexOf(selectedType) === 0}
        >‹</button>
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
        <button
          className="phase-nav-arrow"
          style={{ '--tab-color': tabColor }}
          onClick={() => {
            const i = TYPE_ORDER.indexOf(selectedType);
            if (i < TYPE_ORDER.length - 1) handleTypeTab(TYPE_ORDER[i + 1]);
          }}
          disabled={TYPE_ORDER.indexOf(selectedType) === TYPE_ORDER.length - 1}
        >›</button>
      </div>

      {typedPhases.length === 0 ? (
        <div className="phase-nav-tile phase-nav-tile--empty">
          <span className="phase-nav-tile-empty-text">No phases yet</span>
          {isAuthenticated && (
            <button
              className="phase-pill-add"
              style={{ '--tab-color': tabColor }}
              onClick={() => onAddPhase(selectedType)}
            >
              + Add
            </button>
          )}
        </div>
      ) : isEditing ? (
        <div className="phase-nav-tile phase-nav-tile--editing">
          <div className="pill-edit-dates" style={{ flex: 1 }}>
            <input
              className="pill-edit-input"
              placeholder="Name"
              value={editFields.name}
              onChange={e => setEditFields(f => ({ ...f, name: e.target.value }))}
              autoFocus
            />
            <input
              type="date"
              className="pill-edit-input"
              value={editFields.startDate}
              onChange={e => setEditFields(f => ({ ...f, startDate: e.target.value }))}
            />
            <span className="pill-edit-dash">–</span>
            <input
              type="date"
              className="pill-edit-input"
              value={editFields.endDate}
              onChange={e => setEditFields(f => ({ ...f, endDate: e.target.value }))}
            />
          </div>
          <div className="pill-edit-actions">
            <button className="btn btn-primary btn-xs" onClick={saveEdit}>Save</button>
            <button className="btn btn-ghost btn-xs" onClick={cancelEdit}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className="phase-nav-tile" style={{ '--tab-color': tabColor }}>
          <button
            className="phase-nav-arrow"
            onClick={handlePrev}
            disabled={safeIdx === 0}
            title="Previous phase"
          >‹</button>

          <div
            className={`phase-nav-tile-body${visiblePhase?.phaseId === selectedPhaseId ? ' phase-nav-tile-body--active' : ''}`}
            onClick={() => visiblePhase && selectAndScroll(visiblePhase.phaseId)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && visiblePhase && selectAndScroll(visiblePhase.phaseId)}
          >
            <div className="phase-nav-tile-name">
              {visiblePhase?.name || '(unnamed)'}
              {typedPhases.length > 1 && (
                <span className="phase-nav-tile-counter">{safeIdx + 1} / {typedPhases.length}</span>
              )}
            </div>
            <div className="phase-nav-tile-dates">
              {formatDate(visiblePhase?.startDate)}
              {visiblePhase?.endDate ? ` – ${formatDate(visiblePhase.endDate)}` : ''}
            </div>
          </div>

          <div className="phase-nav-tile-actions">
            {isAuthenticated && (
              <>
                <button className="pill-action-btn" title="Edit" onClick={startEdit}>✎</button>
                <button
                  className="pill-action-btn pill-action-btn--danger"
                  title="Delete"
                  onClick={e => { e.stopPropagation(); setConfirmPhaseId(visiblePhase.phaseId); }}
                >×</button>
              </>
            )}
            {isAuthenticated && (
              <button
                className="phase-pill-add phase-pill-add--inline"
                style={{ '--tab-color': tabColor }}
                onClick={() => onAddPhase(selectedType)}
                title={`Add ${TYPE_CONFIG[selectedType].label} phase`}
              >+</button>
            )}
          </div>

          <button
            className="phase-nav-arrow"
            onClick={handleNext}
            disabled={safeIdx === typedPhases.length - 1}
            title="Next phase"
          >›</button>
        </div>
      )}

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

import { useState, useEffect, useMemo } from 'react';
import { getExport } from '../../api/client.js';
import './DataPage.css';

/* Tab-separated, because the destination is a spreadsheet: pasting TSV into
   Sheets or Excel fills columns, while CSV lands in one cell unless you run
   the import dialog. export.py has already stripped tabs and newlines out of
   the values, so nothing here can break the shape. */
function toTsv(columns, rows) {
  return [columns.join('\t'), ...rows.map(r => r.join('\t'))].join('\n');
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API needs a secure context and permission. Fall back to the
    // old selection trick rather than failing silently.
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

function CopyButton({ label, text, disabled }) {
  const [state, setState] = useState('idle');   // idle | done | failed
  useEffect(() => {
    if (state === 'idle') return undefined;
    const t = setTimeout(() => setState('idle'), 1800);
    return () => clearTimeout(t);
  }, [state]);
  return (
    <button
      className="btn btn-ghost data-copy"
      disabled={disabled}
      onClick={async () => setState(await copy(text) ? 'done' : 'failed')}
    >
      {state === 'done' ? '✓ Copied' : state === 'failed' ? 'Copy failed' : label}
    </button>
  );
}

function Table({ table }) {
  // Big tables render collapsed: 444 sets and 228 snack entries would other-
  // wise make the page unscrollable before you reach the one you want. The
  // copy button works either way — it copies every row, not the shown ones.
  const big = table.rows.length > 12;
  const [open, setOpen] = useState(!big);
  const shown = open ? table.rows : table.rows.slice(0, 5);
  const tsv = useMemo(() => toTsv(table.columns, table.rows), [table]);

  return (
    <section className="data-table">
      <header className="data-table-head">
        <button className="data-table-toggle" onClick={() => setOpen(o => !o)}>
          <span className="data-caret">{open ? '▾' : '▸'}</span>
          <span className="data-table-name">{table.label}</span>
          <span className="data-table-count">
            {table.rows.length} {table.rows.length === 1 ? 'row' : 'rows'}
            {table.truncated && ' (capped)'}
          </span>
        </button>
        <CopyButton label="Copy" text={tsv} disabled={table.rows.length === 0} />
      </header>

      {table.rows.length === 0 ? (
        <div className="data-empty">empty</div>
      ) : (
        <div className="data-scroll">
          <table>
            <thead>
              <tr>{table.columns.map(c => <th key={c}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {shown.map((r, i) => (
                <tr key={i}>{r.map((v, j) => <td key={j}>{v}</td>)}</tr>
              ))}
            </tbody>
          </table>
          {!open && (
            <button className="data-more" onClick={() => setOpen(true)}>
              Show all {table.rows.length} rows
            </button>
          )}
        </div>
      )}
    </section>
  );
}

export default function DataPage({ onBack }) {
  const [tables, setTables] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let alive = true;
    getExport()
      .then(d => { if (alive) setTables(d.tables || []); })
      .catch(e => { if (alive) setErr(e.message); });
    return () => { alive = false; };
  }, []);

  // One blob with every table, each under its own heading — for dropping the
  // lot into a single sheet rather than copying eighteen times.
  const allTsv = useMemo(() => !tables ? '' : tables
    .filter(t => t.rows.length)
    .map(t => `# ${t.label} (${t.name})\n${toTsv(t.columns, t.rows)}`)
    .join('\n\n'), [tables]);

  const totalRows = tables ? tables.reduce((n, t) => n + t.rows.length, 0) : 0;

  return (
    <div className="data-page">
      <div className="data-page-head">
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <span className="card-title" style={{ marginBottom: 0 }}>Data</span>
        {tables && (
          <CopyButton label={`Copy all (${totalRows})`} text={allTsv}
                      disabled={!totalRows} />
        )}
      </div>

      <p className="data-note">
        Everything stored about your training, as it sits in the database.
        Copy puts it on the clipboard tab-separated, which pastes into Sheets
        or Excel as columns.
      </p>

      {err && <div className="exq-error">{err}</div>}
      {!tables && !err && <div className="data-empty">Loading…</div>}
      {tables && tables.map(t => <Table key={t.name} table={t} />)}
    </div>
  );
}

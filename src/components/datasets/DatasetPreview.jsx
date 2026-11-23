import React from 'react';

export function DatasetPreview({ dataset, preview, mode, limit, onMode, onLimit, onPage }) {
  const rows = preview?.rows || dataset.preview || [];
  const columns = dataset.columns || [];
  const offset = preview?.offset || 0;
  return (
    <section className="dataset-preview">
      <div className="preview-toolbar">
        <label>Rows
          <select value={mode} onChange={(event) => onMode(event.target.value)}>
            <option value="first">First rows</option>
            <option value="last">Last rows</option>
            <option value="random">Random sample</option>
          </select>
        </label>
        <label>Count
          <select value={limit} onChange={(event) => onLimit(Number(event.target.value))}>
            {[10, 25, 50].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
      </div>
      <div className="table-wrap">
        <table>
          <caption className="sr-only">Preview of uploaded dataset rows</caption>
          <thead><tr>{columns.map((column) => <th key={column.name}>{column.name}<small>{column.dtype}</small></th>)}</tr></thead>
          <tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column.name}>{String(row[column.name] ?? '—')}</td>)}</tr>)}</tbody>
        </table>
      </div>
      {mode === 'first' && (
        <div className="pager">
          <button disabled={offset === 0} onClick={() => onPage(Math.max(0, offset - limit))}>Previous</button>
          <span>Rows {offset + 1}–{Math.min(offset + rows.length, dataset.summary.rows)} of {dataset.summary.rows.toLocaleString()}</span>
          <button disabled={offset + limit >= dataset.summary.rows} onClick={() => onPage(offset + limit)}>Next</button>
        </div>
      )}
    </section>
  );
}

import React, { useMemo, useState } from 'react';

const types = ['numeric', 'categorical', 'date', 'boolean'];

function display(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
  return String(value);
}

export function EdaColumns({ profiles, overrides, onOverride }) {
  const [search, setSearch] = useState('');
  const visible = useMemo(() => profiles.filter((item) => item.name.toLowerCase().includes(search.toLowerCase())), [profiles, search]);
  return <div>
    <div className="column-tools"><label>Search columns<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Column name…" /></label><span>{visible.length} of {profiles.length} columns</span></div>
    <div className="table-wrap profile-table-wrap"><table className="profile-table"><thead><tr><th>Column</th><th>Effective type</th><th>Original type</th><th>Complete</th><th>Missing</th><th>Unique</th><th>Most frequent</th><th>Statistics</th></tr></thead>
      <tbody>{visible.map((item) => <tr key={item.name}><td><strong>{item.name}</strong>{item.likely_id && <span className="badge warning">Likely ID</span>}</td>
        <td><select aria-label={`Type for ${item.name}`} value={overrides[item.name] || item.effective_type} onChange={(event) => onOverride(item.name, event.target.value, item.detected_type)}>{types.map((type) => <option key={type}>{type}</option>)}</select>{overrides[item.name] && <small>Overridden</small>}</td>
        <td>{item.original_type}</td><td>{item.non_null.toLocaleString()}</td><td>{item.null_count.toLocaleString()} ({item.null_pct}%)</td><td>{item.unique.toLocaleString()} ({item.unique_pct}%)</td><td>{display(item.most_frequent)} <small>× {item.most_frequent_count}</small></td>
        <td><div className="profile-stats">{Object.entries(item.statistics || {}).filter(([, value]) => !Array.isArray(value)).slice(0, 6).map(([key, value]) => <span className="profile-stat" key={key}><b>{key.replaceAll('_', ' ')}</b><span className="profile-stat-value">{display(value)}</span></span>)}</div></td>
      </tr>)}</tbody></table></div>
  </div>;
}

import React, { useMemo, useState } from 'react';

export function EdaQuality({ quality }) {
  const [severity, setSeverity] = useState('all');
  const visible = useMemo(() => quality.issues.filter((item) => severity === 'all' || item.severity === severity), [quality, severity]);
  return <div>
    <div className="quality-counters">
      {['critical', 'warning', 'information'].map((level) => <button className={severity === level ? 'active' : ''} onClick={() => setSeverity(severity === level ? 'all' : level)} key={level}><strong>{quality.counts[level]}</strong><span>{level}</span></button>)}
    </div>
    <p className="muted">{quality.complete_rows.toLocaleString()} complete rows · {quality.incomplete_rows.toLocaleString()} rows contain at least one missing value. Findings are advisory; no data has been changed.</p>
    {visible.length ? <div className="issue-list">{visible.map((item, index) => <article className={`quality-issue ${item.severity}`} key={`${item.code}-${item.column}-${index}`}>
      <div><span className="severity">{item.severity}</span>{item.column && <span className="issue-column">{item.column}</span>}</div>
      <h3>{item.title}</h3><p>{item.detail}</p><p className="suggested-action"><strong>Suggested action:</strong> {item.suggested_action}</p>
    </article>)}</div> : <div className="analytics-empty"><div className="empty-icon">✓</div><div><h3>No matching findings</h3><p>No issues were found for this severity filter.</p></div></div>}
  </div>;
}

import React from 'react';
import { MetricCard } from '../../components/ui/MetricCard';

function bytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

export function EdaOverview({ dataset }) {
  const summary = dataset.summary;
  const metrics = [
    ['Rows', summary.rows.toLocaleString()], ['Columns', summary.columns],
    ['Numeric', summary.numeric_columns], ['Categorical', summary.categorical_columns],
    ['Dates', summary.date_columns], ['Boolean', summary.boolean_columns],
    ['Constant', summary.constant_columns], ['High cardinality', summary.high_cardinality_columns],
    ['Missing cells', summary.missing_values.toLocaleString()], ['Duplicate rows', summary.duplicates.toLocaleString()],
    ['Memory', bytes(summary.memory_bytes)],
  ];
  return <div>
    <div className="metric-grid eda-metrics">{metrics.map(([label, value]) => <MetricCard label={label} value={value} key={label} />)}</div>
    <section className="quality-summary">
      <h3>Dataset structure</h3>
      <p>{summary.rows.toLocaleString()} records across {summary.columns} columns are held only in this local backend session.</p>
      <div className="type-pills">{['numeric', 'categorical', 'date', 'boolean', 'constant'].map((kind) => <span key={kind}>{summary[`${kind}_columns`]} {kind}</span>)}</div>
    </section>
  </div>;
}

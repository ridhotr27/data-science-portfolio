import React from 'react';

export function ChartContainer({ title, description, children }) {
  return (
    <section className="chart-container">
      <header><h3>{title}</h3>{description && <p>{description}</p>}</header>
      <div className="chart-content">{children}</div>
    </section>
  );
}

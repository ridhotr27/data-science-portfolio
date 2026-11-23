import React from 'react';

export function Card({ title, eyebrow, children, className = '' }) {
  return (
    <section className={`ml-card ${className}`}>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h2 className="card-title">{title}</h2>
      {children}
    </section>
  );
}

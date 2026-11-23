import React from 'react';

export function EmptyState({ title, description, items = [] }) {
  return (
    <div className="analytics-empty">
      <div className="empty-icon" aria-hidden="true">+</div>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
        {items.length > 0 && (
          <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
        )}
      </div>
    </div>
  );
}

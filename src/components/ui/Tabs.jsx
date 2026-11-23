import React from 'react';

export function Tabs({ tabs, active, onChange, label = 'Analysis sections' }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button type="button" role="tab" aria-selected={active === tab.id}
          className={active === tab.id ? 'active' : ''} onClick={() => onChange(tab.id)} key={tab.id}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}

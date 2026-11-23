import React from 'react';

export function LoadingState({ label = 'Loading analysis…' }) {
  return <div className="loading-state" role="status"><span />{label}</div>;
}

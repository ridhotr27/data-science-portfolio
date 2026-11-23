import React from 'react';

export function ErrorState({ message, onRetry }) {
  return (
    <div className="alert error" role="alert">
      <span>{message}</span>
      {onRetry && <button type="button" onClick={onRetry}>Try again</button>}
    </div>
  );
}

import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    if (import.meta.env.DEV) console.error('Application render error', error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="fatal-error" role="alert">
        <p className="eyebrow">Something went wrong</p>
        <h1>This view could not be displayed.</h1>
        <p>{this.state.error.message || 'An unexpected interface error occurred.'}</p>
        <button className="button primary compact" onClick={() => window.location.reload()}>
          Reload this page
        </button>
      </main>
    );
  }
}

import React from 'react';

export function AppHeader({ sections = [] }) {
  return (
    <header className="navbar">
      <a className="brand" href="/" aria-label="Portfolio home">
        Ridho Trivonanda
      </a>
      <nav className="nav-links" aria-label="Main navigation">
        <a href="/">Portfolio</a>
        {sections.map((section) => (
          <a href={`#${section.id}`} key={section.id}>{section.label}</a>
        ))}
      </nav>
    </header>
  );
}

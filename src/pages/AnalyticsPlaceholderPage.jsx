import React, { useState } from 'react';
import { AppFooter } from '../components/layout/AppFooter';
import { AppHeader } from '../components/layout/AppHeader';
import { DatasetWorkspace } from '../components/datasets/DatasetWorkspace';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Tabs } from '../components/ui/Tabs';

export function AnalyticsPlaceholderPage({ eyebrow, title, description, tabs, capabilities }) {
  const [active, setActive] = useState(tabs[0].id);
  const [dataset, setDataset] = useState(null);

  return (
    <div className="site">
      <AppHeader sections={[{ id: 'workspace', label: 'Workspace' }]} />
      <main className="ml-main">
        <section className="ml-hero analytics-hero">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <div className="analytics-capabilities">
            {capabilities.map((item) => <span key={item}>{item}</span>)}
          </div>
        </section>
        <p className="privacy-note">Uploaded files will be processed only by the local analytics backend. Do not upload confidential data to an untrusted deployment.</p>
        <Card title="Analysis workspace" eyebrow="Milestone 1" className="analytics-workspace">
          <DatasetWorkspace onDataset={setDataset} />
          <Tabs tabs={tabs} active={active} onChange={setActive} />
          <EmptyState title={dataset ? `${tabs.find((tab) => tab.id === active)?.label} analysis comes next` : 'Upload a dataset to begin'}
            description={dataset ? 'The dataset is validated and available to this local session. Analytics calculations will be connected in the approved feature milestones.' : 'CSV and XLSX files are validated and processed by the local FastAPI backend.'}
            items={capabilities} />
        </Card>
      </main>
      <AppFooter />
    </div>
  );
}

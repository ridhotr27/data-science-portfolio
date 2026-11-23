import React, { useEffect, useRef, useState } from 'react';
import { edaApi } from '../api/eda';
import { DatasetWorkspace } from '../components/datasets/DatasetWorkspace';
import { DataRequirements } from '../components/datasets/DataRequirements';
import { AppFooter } from '../components/layout/AppFooter';
import { AppHeader } from '../components/layout/AppHeader';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { Tabs } from '../components/ui/Tabs';
import { EdaColumns } from '../features/eda/EdaColumns';
import { EdaDistributions } from '../features/eda/EdaDistributions';
import { EdaInsights } from '../features/eda/EdaInsights';
import { EdaOverview } from '../features/eda/EdaOverview';
import { EdaOutliers } from '../features/eda/EdaOutliers';
import { EdaQuality } from '../features/eda/EdaQuality';
import { EdaRelationships } from '../features/eda/EdaRelationships';
import { EdaTarget } from '../features/eda/EdaTarget';

const tabs = ['Overview', 'Data Quality', 'Columns', 'Distributions', 'Relationships', 'Target Analysis', 'Outliers', 'Insights']
  .map((label) => ({ id: label.toLowerCase().replaceAll(' ', '-'), label }));

export function EdaPage() {
  const [dataset, setDataset] = useState(null);
  const [active, setActive] = useState('overview');
  const [profiles, setProfiles] = useState([]);
  const [quality, setQuality] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const analysisRequest = useRef(0);

  async function analyze(current = dataset, nextOverrides = overrides) {
    if (!current) return;
    const requestId = ++analysisRequest.current;
    setBusy(true); setError('');
    try {
      const [profileResult, qualityResult] = await Promise.all([
        edaApi.profile(current.dataset_id, nextOverrides),
        edaApi.quality(current.dataset_id, nextOverrides),
      ]);
      if (requestId === analysisRequest.current) { setProfiles(profileResult.profiles); setQuality(qualityResult); }
    } catch (analysisError) { if (requestId === analysisRequest.current) setError(analysisError.message); }
    finally { if (requestId === analysisRequest.current) setBusy(false); }
  }

  useEffect(() => {
    analysisRequest.current += 1;
    setOverrides({});
    setProfiles([]);
    setQuality(null);
    if (dataset) analyze(dataset, {});
  }, [dataset?.dataset_id]);

  function override(name, value, detected) {
    const next = { ...overrides };
    if (value === detected) delete next[name]; else next[name] = value;
    setOverrides(next); analyze(dataset, next);
  }

  let content;
  if (!dataset) content = <EmptyState title="Upload a dataset to begin" description="CSV and XLSX files are processed by the local FastAPI backend." />;
  else if (busy && !profiles.length) content = <LoadingState label="Profiling columns and evaluating data quality…" />;
  else if (active === 'overview') content = <EdaOverview dataset={dataset} />;
  else if (active === 'data-quality') content = quality && <EdaQuality quality={quality} />;
  else if (active === 'columns') content = <EdaColumns profiles={profiles} overrides={overrides} onOverride={override} />;
  else if (active === 'distributions') content = <EdaDistributions dataset={dataset} profiles={profiles} overrides={overrides} />;
  else if (active === 'relationships') content = <EdaRelationships dataset={dataset} profiles={profiles} overrides={overrides} />;
  else if (active === 'target-analysis') content = <EdaTarget dataset={dataset} profiles={profiles} overrides={overrides} onTarget={setTarget} />;
  else if (active === 'outliers') content = <EdaOutliers dataset={dataset} profiles={profiles} overrides={overrides} />;
  else if (active === 'insights') content = <EdaInsights dataset={dataset} profiles={profiles} overrides={overrides} target={target} />;

  return <div className="site"><AppHeader sections={[{ id: 'workspace', label: 'Workspace' }]} /><main className="ml-main">
    <section className="ml-hero analytics-hero"><div><p className="eyebrow">Dataset diagnostics</p><h1>Exploratory Data Analysis</h1><p>Inspect structure, quality, missingness, and modelling risks before drawing conclusions from a dataset.</p></div><div className="analytics-capabilities"><span>Automated profiling</span><span>Quality & anomaly checks</span><span>Explicit type overrides</span></div></section>
    <p className="privacy-note">Uploaded files remain in the local backend session and expire after inactivity. No cleaning action is applied automatically.</p>
    <DataRequirements type="eda" />
    <Card title="Dataset" eyebrow="Upload & validate"><DatasetWorkspace onDataset={setDataset} /></Card>
    <Card title="Exploration workspace" eyebrow="Milestone 3" className="analytics-workspace" id="workspace">
      <Tabs tabs={tabs} active={active} onChange={setActive} />
      {error && <ErrorState message={error} onRetry={() => analyze()} />}
      {busy && profiles.length > 0 && <LoadingState label="Refreshing analysis…" />}
      {content}
    </Card>
  </main><AppFooter /></div>;
}

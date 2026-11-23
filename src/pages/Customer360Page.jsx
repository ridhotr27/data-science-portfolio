import React, { useState } from 'react';
import { DatasetWorkspace } from '../components/datasets/DatasetWorkspace';
import { DataRequirements } from '../components/datasets/DataRequirements';
import { AppFooter } from '../components/layout/AppFooter';
import { AppHeader } from '../components/layout/AppHeader';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { ColumnMapping } from '../features/customer360/ColumnMapping';
import { CustomerDashboard } from '../features/customer360/CustomerDashboard';

export function Customer360Page() {
  const [dataset,setDataset]=useState(null),[configuration,setConfiguration]=useState(null),[mapping,setMapping]=useState(null);
  function changed(next){setDataset(next);setConfiguration(null);setMapping(null)}
  return <div className="site"><AppHeader sections={[{id:'workspace',label:'Workspace'}]}/><main className="ml-main">
    <section className="ml-hero analytics-hero"><div><p className="eyebrow">Customer intelligence</p><h1>Customer 360 Analytics</h1><p>Understand customer value, behavior, engagement, retention, and segmentation using locally processed transaction data.</p></div><div className="analytics-capabilities"><span>Flexible column mapping</span><span>RFM & cohort analysis</span><span>Customer-level insights</span></div></section>
    <p className="privacy-note">Customer data stays in this local session. Sensitive-looking mapped attributes are masked by default in individual profiles.</p>
    <DataRequirements type="customer360" />
    <Card title="Dataset" eyebrow="Upload & validate"><DatasetWorkspace onDataset={changed}/></Card>
    {dataset&&<Card title="Map customer data" eyebrow="Configure"><ColumnMapping dataset={dataset} onConfigured={(config,map)=>{setConfiguration(config);setMapping(map)}}/></Card>}
    {dataset&&configuration&&<Card title="Customer analytics" eyebrow="Dashboard" className="analytics-workspace"><CustomerDashboard dataset={dataset} configuration={configuration} mapping={mapping}/></Card>}
    {!dataset&&<Card title="Customer analytics" eyebrow="Dashboard"><EmptyState title="Upload a dataset to begin" description="Only Customer ID is required. Additional mappings progressively enable revenue, RFM, retention, behavior, and CLV analysis."/></Card>}
  </main><AppFooter/></div>;
}

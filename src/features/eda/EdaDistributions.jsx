import React, { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { edaApi } from '../../api/eda';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';

export function EdaDistributions({ dataset, profiles, overrides }) {
  const [column, setColumn] = useState(profiles[0]?.name || '');
  const [bins, setBins] = useState(20);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function load() {
    if (!column) return;
    setBusy(true); setError('');
    try { setResult(await edaApi.distribution(dataset.dataset_id, { column, bins, top_n: 10, date_frequency: 'month', overrides })); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  useEffect(() => { load(); }, [column, bins, JSON.stringify(overrides)]);
  const chart = result?.histogram?.map((item) => ({ label: Number(item.start).toPrecision(3), count: item.count }))
    || result?.categories?.map((item) => ({ label: item.value, count: item.count }))
    || result?.series?.map((item) => ({ label: item.period, count: item.count })) || [];
  return <div><div className="analysis-controls"><label>Column<select value={column} onChange={(e) => setColumn(e.target.value)}>{profiles.map((item) => <option key={item.name}>{item.name}</option>)}</select></label>
    {result?.type === 'numeric' && <label>Histogram bins<input type="number" min="5" max="100" value={bins} onChange={(e) => setBins(Number(e.target.value))} /></label>}</div>
    {busy && <LoadingState label="Calculating distribution…" />}{error && <ErrorState message={error} onRetry={load} />}
    {result && <><div className="chart-panel"><ResponsiveContainer width="100%" height={320}><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#273249"/><XAxis dataKey="label" stroke="#94a3b8" tick={{fontSize:11}}/><YAxis stroke="#94a3b8"/><Tooltip contentStyle={{background:'#111a2d',border:'1px solid #334155'}}/><Bar dataKey="count" fill="#06b6d4" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div>
      <div className="metric-grid eda-metrics">{Object.entries(result.summary || {}).filter(([,v]) => typeof v !== 'object').map(([key,value]) => <div className="stat" key={key}><span>{key.replaceAll('_',' ')}</span><strong>{typeof value === 'number' ? value.toFixed(3) : String(value)}</strong></div>)}</div></>}
  </div>;
}

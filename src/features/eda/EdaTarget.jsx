import React, { useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { edaApi } from '../../api/eda';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';

export function EdaTarget({dataset,profiles,overrides,onTarget}) {
  const [target,setTarget]=useState(''),[problem,setProblem]=useState('auto'),[result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function load(){if(!target)return;setBusy(true);setError('');try{const data=await edaApi.target(dataset.dataset_id,{target,problem_type:problem,overrides});setResult(data);onTarget(target);}catch(e){setError(e.message)}finally{setBusy(false)}}
  return <div><div className="analysis-controls"><label>Target column<select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Choose target…</option>{profiles.map(p=><option key={p.name}>{p.name}</option>)}</select></label><label>Problem type<select value={problem} onChange={e=>setProblem(e.target.value)}><option value="auto">Automatic recommendation</option><option value="binary_classification">Binary classification</option><option value="multiclass_classification">Multiclass classification</option><option value="regression">Regression</option><option value="time_series_regression">Time-series regression</option></select></label><button onClick={load} disabled={!target}>Analyze target</button></div>
    {busy&&<LoadingState label="Analyzing target…"/>}{error&&<ErrorState message={error}/>}
    {result&&<><p className="suggestion"><strong>{result.problem_type.replaceAll('_',' ')}</strong><br/>{result.suggestion.reason} This is a recommendation, not a modelling decision.</p>
      {result.classes&&<div className="chart-panel"><ResponsiveContainer width="100%" height={300}><BarChart data={result.classes}><CartesianGrid stroke="#273249"/><XAxis dataKey="value" stroke="#94a3b8"/><YAxis stroke="#94a3b8"/><Tooltip/><Bar dataKey="count" fill="#8b5cf6"/></BarChart></ResponsiveContainer></div>}
      {result.feature_relationships&&<div className="table-wrap"><table><thead><tr><th>Feature</th><th>Absolute target correlation</th></tr></thead><tbody>{result.feature_relationships.map(r=><tr key={r.feature}><td>{r.feature}</td><td>{r.absolute_correlation?.toFixed(3)}</td></tr>)}</tbody></table></div>}</>}
  </div>;
}

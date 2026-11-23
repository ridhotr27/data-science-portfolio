import React, { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';
import { edaApi } from '../../api/eda';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';

export function EdaRelationships({ dataset, profiles, overrides }) {
  const numeric = profiles.filter((p) => (overrides[p.name] || p.effective_type) === 'numeric');
  const [x,setX]=useState(profiles[0]?.name||''), [y,setY]=useState(profiles[1]?.name||profiles[0]?.name||'');
  const [method,setMethod]=useState('pearson'), [threshold,setThreshold]=useState(.7);
  const [correlations,setCorrelations]=useState(null), [relation,setRelation]=useState(null), [busy,setBusy]=useState(false), [error,setError]=useState('');
  async function loadCorrelation(){if(numeric.length<2)return;setBusy(true);setError('');try{setCorrelations(await edaApi.correlation(dataset.dataset_id,{method,threshold,columns:numeric.map(p=>p.name).slice(0,40),overrides}));}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function loadRelation(){if(!x||!y)return;setBusy(true);setError('');try{setRelation(await edaApi.relationship(dataset.dataset_id,{x,y,group:null,overrides}));}catch(e){setError(e.message)}finally{setBusy(false)}}
  useEffect(()=>{loadCorrelation()},[method,threshold,JSON.stringify(overrides)]);
  useEffect(()=>{loadRelation()},[x,y,JSON.stringify(overrides)]);
  return <div><div className="analysis-controls"><label>Correlation<select value={method} onChange={e=>setMethod(e.target.value)}><option>pearson</option><option>spearman</option></select></label><label>Minimum absolute value<input type="number" min="0" max="1" step=".05" value={threshold} onChange={e=>setThreshold(Number(e.target.value))}/></label></div>
    {busy&&<LoadingState label="Calculating relationships…"/>}{error&&<ErrorState message={error}/>}
    {correlations&&<div className="table-wrap correlation-table"><table><thead><tr><th>Feature</th>{correlations.columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{correlations.matrix.map(row=><tr key={row.column}><td>{row.column}</td>{correlations.columns.map(c=><td className={Math.abs(row[c])>=threshold?'strong-correlation':''} key={c}>{row[c]?.toFixed(2)??'—'}</td>)}</tr>)}</tbody></table></div>}
    <h3 className="subheading">Explore two variables</h3><div className="analysis-controls"><label>X variable<select value={x} onChange={e=>setX(e.target.value)}>{profiles.map(p=><option key={p.name}>{p.name}</option>)}</select></label><label>Y variable<select value={y} onChange={e=>setY(e.target.value)}>{profiles.map(p=><option key={p.name}>{p.name}</option>)}</select></label></div>
    {relation&&<RelationshipChart result={relation}/>}<p className="muted">Correlation describes association and does not prove causation.</p>
  </div>;
}

function RelationshipChart({result}) {
  if(result.chart==='contingency') return <div className="table-wrap"><table><thead><tr><th>{result.x}</th>{result.columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{result.points.map(r=><tr key={r.value}><td>{r.value}</td>{result.columns.map(c=><td key={c}>{r[c]||0}</td>)}</tr>)}</tbody></table></div>;
  return <div className="chart-panel"><ResponsiveContainer width="100%" height={320}>
    {result.chart==='scatter'?<ScatterChart><CartesianGrid stroke="#273249"/><XAxis dataKey={result.x} stroke="#94a3b8"/><YAxis dataKey={result.y} stroke="#94a3b8"/><Tooltip/><Scatter data={result.points} fill="#8b5cf6"/></ScatterChart>:
    result.chart==='line'?<LineChart data={result.points}><CartesianGrid stroke="#273249"/><XAxis dataKey="x" stroke="#94a3b8"/><YAxis stroke="#94a3b8"/><Tooltip/><Line dataKey="value" stroke="#06b6d4" dot={false}/></LineChart>:
    <BarChart data={result.points}><CartesianGrid stroke="#273249"/><XAxis dataKey={result.x} stroke="#94a3b8"/><YAxis stroke="#94a3b8"/><Tooltip/><Bar dataKey="mean" fill="#06b6d4"/></BarChart>}
  </ResponsiveContainer></div>;
}

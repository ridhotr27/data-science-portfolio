import React, { useEffect, useState } from 'react';
import { edaApi } from '../../api/eda';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';

export function EdaOutliers({dataset,profiles,overrides}) {
  const numeric=profiles.filter(p=>(overrides[p.name]||p.effective_type)==='numeric');
  const [column,setColumn]=useState(''),[method,setMethod]=useState('iqr'),[threshold,setThreshold]=useState(1.5),[result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function load(){setBusy(true);setError('');try{setResult(await edaApi.outliers(dataset.dataset_id,{column:column||null,method,threshold,limit:50,overrides}));}catch(e){setError(e.message)}finally{setBusy(false)}}
  useEffect(()=>{if(numeric.length)load()},[column,method,threshold,JSON.stringify(overrides)]);
  return <div><div className="analysis-controls"><label>Column<select value={column} onChange={e=>setColumn(e.target.value)}><option value="">All numeric columns</option>{numeric.map(p=><option key={p.name}>{p.name}</option>)}</select></label><label>Method<select value={method} onChange={e=>{setMethod(e.target.value);setThreshold(e.target.value==='iqr'?1.5:3)}}><option value="iqr">IQR</option><option value="zscore">Z-score</option></select></label><label>Threshold<input type="number" min=".5" max="10" step=".5" value={threshold} onChange={e=>setThreshold(Number(e.target.value))}/></label></div>
    <p className="muted">Outliers may be valid business observations. Inspect them before removing or changing data.</p>{busy&&<LoadingState label="Detecting potential outliers…"/>}{error&&<ErrorState message={error}/>}
    {result&&<><div className="table-wrap"><table><thead><tr><th>Column</th><th>Lower threshold</th><th>Upper threshold</th><th>Outliers</th><th>Percentage</th></tr></thead><tbody>{result.summary.map(r=><tr key={r.column}><td>{r.column}</td><td>{r.lower?.toFixed(3)??'—'}</td><td>{r.upper?.toFixed(3)??'—'}</td><td>{r.count}</td><td>{r.pct}%</td></tr>)}</tbody></table></div>{result.rows.length>0&&<div className="table-wrap"><table><thead><tr>{Object.keys(result.rows[0]).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{result.rows.map((r,i)=><tr key={i}>{Object.values(r).map((v,j)=><td key={j}>{String(v??'—')}</td>)}</tr>)}</tbody></table></div>}</>}
  </div>;
}

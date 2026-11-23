import React, { useEffect, useState } from 'react';
import { customer360Api } from '../../api/customer360';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';

const roles = [
  ['customer_id','Customer ID',true],['transaction_date','Transaction date'],['transaction_id','Transaction ID'],
  ['revenue','Revenue / sales'],['quantity','Quantity'],['unit_price','Unit price'],['product','Product'],
  ['category','Product category'],['store','Store'],['channel','Channel'],['registration_date','Registration date'],
  ['city','City'],['gender','Gender'],['age','Age'],
];

export function ColumnMapping({dataset,onConfigured}) {
  const [mapping,setMapping]=useState({currency:'IDR',attributes:[]}),[busy,setBusy]=useState(false),[error,setError]=useState('');
  useEffect(()=>{setBusy(true);customer360Api.suggestions(dataset.dataset_id).then(data=>setMapping({...data.suggestions,currency:'IDR',attributes:[]})).catch(e=>setError(e.message)).finally(()=>setBusy(false))},[dataset.dataset_id]);
  async function configure(){if(!mapping.customer_id)return setError('Customer ID is required.');setBusy(true);setError('');try{onConfigured(await customer360Api.configure(dataset.dataset_id,mapping),mapping)}catch(e){setError(e.message)}finally{setBusy(false)}}
  if(busy&&!mapping.customer_id)return <LoadingState label="Suggesting column mappings…"/>;
  return <div><p className="muted">Confirm semantic roles. Only Customer ID is required; unavailable analyses will explain their missing inputs.</p><div className="mapping-grid">{roles.map(([key,label,required])=><label key={key}>{label}{required&&<b>Required</b>}<select value={mapping[key]||''} onChange={e=>setMapping(m=>({...m,[key]:e.target.value||null}))}><option value="">Not mapped</option>{dataset.columns.map(c=><option key={c.name}>{c.name}</option>)}</select></label>)}<label>Currency<select value={mapping.currency} onChange={e=>setMapping(m=>({...m,currency:e.target.value}))}><option>IDR</option><option>USD</option><option>EUR</option><option>SGD</option><option>AUD</option></select></label></div>{error&&<ErrorState message={error}/>}<div className="actions"><button className="button primary compact" onClick={configure} disabled={busy}>Build Customer 360</button></div></div>;
}

import React, { useEffect, useState } from 'react';
import { edaApi } from '../../api/eda';
import { ErrorState } from '../../components/ui/ErrorState';
import { LoadingState } from '../../components/ui/LoadingState';

export function EdaInsights({dataset,profiles,overrides,target}) {
  const [insights,setInsights]=useState([]),[readiness,setReadiness]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function load(){setBusy(true);setError('');try{const selected=target||profiles[0]?.name;const [a,b]=await Promise.all([edaApi.insights(dataset.dataset_id,overrides),edaApi.readiness(dataset.dataset_id,{target:selected,problem_type:'auto',overrides})]);setInsights(a.insights);setReadiness(b);}catch(e){setError(e.message)}finally{setBusy(false)}}
  useEffect(()=>{load()},[target,JSON.stringify(overrides)]);
  async function download(type){try{await edaApi.export(dataset.dataset_id,{export_type:type,method:type==='outliers'?'iqr':'pearson',threshold:1.5,overrides},`eda_${type}.${type==='summary'?'json':'csv'}`)}catch(e){setError(e.message)}}
  return <div>{busy&&<LoadingState label="Generating calculated insights…"/>}{error&&<ErrorState message={error}/>}
    {readiness&&<><div className={`readiness ${readiness.status.toLowerCase().replaceAll(' ','-')}`}><span>Modelling readiness</span><strong>{readiness.status}</strong><p>{readiness.explanation}</p></div><div className="readiness-checks">{readiness.checks.map(c=><div key={c.name}><span className={c.level}>{c.level}</span><strong>{c.name}</strong><p>{c.detail}</p></div>)}</div></>}
    <h3 className="subheading">Calculated insights</h3><div className="insight-list">{insights.map((item,i)=><p key={i}><span>{i+1}</span>{item.text}</p>)}</div>
    <h3 className="subheading">Exports</h3><div className="download-row">{['profiles','quality','correlation','outliers','summary'].map(type=><button className="button secondary compact" onClick={()=>download(type)} key={type}>{type.replaceAll('_',' ')}</button>)}</div>
  </div>;
}

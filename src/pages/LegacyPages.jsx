import React, { useEffect, useRef, useState } from 'react';
import '../styles.css';

const API = import.meta.env.VITE_API_URL
  || (import.meta.env.PROD ? window.location.origin : 'http://localhost:8000');
const MAX_FILE_SIZE = 5 * 1024 * 1024;
const XGBOOST_ENABLED = import.meta.env.VITE_ENABLE_XGBOOST === 'true';

const skillGroups = [
  { category: 'Programming & Databases', items: ['Python', 'SQL', 'PostgreSQL', 'FastAPI'] },
  { category: 'Machine Learning & Data Science', items: ['Machine Learning', 'Recommendation Systems', 'Data Modeling', 'Scikit-learn'] },
  { category: 'Data Engineering & Analytics', items: ['ETL/ELT Pipelines', 'Data Visualization', 'ClickHouse', 'Prefect'] },
  { category: 'AI & Emerging Technologies', items: ['LLMs & RAG', 'LangChain', 'LangGraph', 'Vector Database'] },
];

const brandIcons = {
  Python: 'python', PostgreSQL: 'postgresql', FastAPI: 'fastapi',
  'Scikit-learn': 'scikitlearn', ClickHouse: 'clickhouse', Prefect: 'prefect',
  LangChain: 'langchain', LangGraph: 'langgraph',
};

const conceptIcons = {
  SQL: 'database', 'Machine Learning': 'network', 'Recommendation Systems': 'recommendation',
  'Data Modeling': 'model', 'ETL/ELT Pipelines': 'pipeline', 'Data Visualization': 'chart',
  'LLMs & RAG': 'language', 'Vector Database': 'vector',
};
const projects = [
  { title: 'Indonesia Wildfire Intelligence — LLM & RAG', description: 'An AI-powered wildfire intelligence platform combining Large Language Models, Retrieval-Augmented Generation, and satellite data analytics to explore wildfire activity across Indonesia. It brings together natural-language questions, data analysis, and interactive visualizations.', tech: ['Python', 'FastAPI', 'LangGraph', 'RAG', 'ClickHouse', 'Docker'], status: 'Live', href: 'https://wildfire.ridhotrivo.com', linkLabel: 'Live Demo', external: true, featured: true },
  { title: 'XGBoost Model Builder', description: 'Upload a dataset, configure a real XGBoost pipeline, and explore evaluation results.', tech: ['Python', 'FastAPI', 'Scikit-learn', 'XGBoost', 'Pandas', 'React'], href: XGBOOST_ENABLED ? '/projects/xgboost-predictor' : null, featured: true, unavailable: !XGBOOST_ENABLED },
  { title: 'Customer 360 Analytics', description: 'Explore customer value, behavior, RFM segments, retention, and lifetime value from your own data.', tech: ['Python', 'FastAPI', 'Pandas', 'NumPy', 'React'], href: '/projects/customer-360', featured: true },
  { title: 'Exploratory Data Analysis', description: 'Profile dataset quality, distributions, relationships, anomalies, and modelling readiness.', tech: ['Python', 'FastAPI', 'Pandas', 'NumPy', 'SciPy', 'React'], href: '/projects/exploratory-data-analysis', featured: true },
  { title: 'Recommendation System', description: 'Built a personalized product recommendation engine using customer behavior data and similarity scoring.' },
  { title: 'Demand Forecasting', description: 'Created time-series forecasts to help operations teams plan inventory and reduce stockout risk.' },
  { title: 'Automated Dashboard', description: 'Designed a reporting dashboard that refreshes pipeline metrics and business KPIs automatically.' },
];

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'The server could not complete this request.');
  return data;
}

function Header({ app = false }) {
  return <header className="navbar">
    <a className="brand" href="/" aria-label="Portfolio home">Ridho Trivonanda</a>
    <nav className="nav-links" aria-label="Main navigation">
      {app ? <><a href="/">Portfolio</a><a href="#builder">Builder</a><a href="#results">Results</a></> :
        <><a href="#home">Home</a><a href="#about">About</a><a href="#projects">Projects</a><a href="#contact">Contact</a></>}
    </nav>
  </header>;
}

function Footer() {
  return <footer className="footer"><p>© 2026 Ridho Trivonanda. All rights reserved.</p></footer>;
}

function SkillCategoryIcon({ index }) {
  const paths = [
    <><path d="M8 8 4 12l4 4M16 8l4 4-4 4M14 4l-4 16"/><ellipse cx="12" cy="4" rx="8" ry="2.5"/></>,
    <><circle cx="6" cy="7" r="2.5"/><circle cx="18" cy="7" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="m8 8.5 3 7M16 8.5l-3 7M8.5 7h7"/></>,
    <><rect x="3" y="4" width="6" height="5" rx="1"/><rect x="15" y="15" width="6" height="5" rx="1"/><path d="M9 6.5h5a3 3 0 0 1 3 3V15M15 17.5h-5a3 3 0 0 1-3-3V9"/></>,
    <><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z"/><path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z"/></>,
  ];
  return <svg className="skill-category-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[index]}</svg>;
}

function ConceptSkillIcon({ type = 'database' }) {
  const paths = {
    database: <><ellipse cx="12" cy="5" rx="7.5" ry="3"/><path d="M4.5 5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V5M4.5 11v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6"/></>,
    network: <><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="7" r="2.5"/><circle cx="11" cy="18" r="2.5"/><path d="m8 7.2 7.5-.2M7.2 8.2l2.7 7.5m6.6-6.5-4 6.7"/></>,
    recommendation: <><circle cx="7" cy="8" r="3"/><circle cx="17" cy="8" r="3"/><path d="M2.5 19c.7-3 2.2-5 4.5-5s3.8 2 4.5 5M13.5 18l2 2 4-5"/></>,
    model: <><rect x="3" y="3" width="7" height="6" rx="1"/><rect x="14" y="15" width="7" height="6" rx="1"/><path d="M10 6h4a3 3 0 0 1 3 3v6M14 18h-4a3 3 0 0 1-3-3V9"/></>,
    pipeline: <><rect x="2.5" y="5" width="5" height="5" rx="1"/><rect x="16.5" y="14" width="5" height="5" rx="1"/><path d="M7.5 7.5h5a4 4 0 0 1 4 4V14M13.5 11l3 3 3-3"/></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></>,
    language: <><path d="M4 4h12a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H9l-5 4v-4a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3Z"/><path d="m15 7 .7 2.3L18 10l-2.3.7L15 13l-.7-2.3L12 10l2.3-.7L15 7Z"/></>,
    vector: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/><circle cx="9" cy="11" r=".8" fill="currentColor"/><circle cx="13" cy="17" r=".8" fill="currentColor"/></>,
  };
  return <svg className="skill-row-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[type]}</svg>;
}

function SkillIcon({ name }) {
  const [failed, setFailed] = useState(false);
  const slug = brandIcons[name];
  if (slug && !failed) return <img className="skill-brand-icon" src={`https://cdn.simpleicons.org/${slug}`} alt="" aria-hidden="true" onError={() => setFailed(true)}/>;
  return <ConceptSkillIcon type={conceptIcons[name] || 'database'}/>;
}

export function PortfolioPage() {
  return <div className="site"><Header /><main>
    <section className="hero" id="home"><div className="hero-content">
      <p className="eyebrow">Data Scientist / Data Engineer</p>
      <h1>Hi, I&apos;m Ridho Trivonanda! 👋</h1>
      <p className="hero-text">I&apos;m a Data Scientist and Data Engineer who enjoys turning complex data into meaningful insights. I build machine learning models, data pipelines, and analytics solutions to solve real-world business problems.</p>
      <div className="hero-actions"><a className="button primary" href="#projects">View Projects</a><a className="button secondary" href="#contact">Contact Me</a></div>
    </div></section>
    <section className="section" id="about"><div className="section-heading"><p className="eyebrow">About</p><h2>A Little About Me</h2></div>
      <p className="section-copy">I love working with data, from building machine learning models and data pipelines to uncovering meaningful insights. One of my proudest achievements is developing a recommendation system that contributes to 50% of total hires. I&apos;m always curious, enjoy solving new challenges, and currently exploring LLMs, RAG, and AI-powered applications.</p>
    </section>
    <section className="section skills-section"><div className="section-heading"><h2>Technologies &amp; Expertise</h2></div>
      <div className="skills-grid">{skillGroups.map((group, index) => <article className="skill-category" key={group.category}><h3><SkillCategoryIcon index={index}/><span>{group.category}</span></h3><div className="skill-list">{group.items.map(skill => <span className="skill-chip" key={skill}><SkillIcon name={skill}/><span>{skill}</span></span>)}</div></article>)}</div>
    </section>
    <section className="section" id="projects"><div className="section-heading"><p className="eyebrow">Projects</p><h2>Selected Work</h2></div>
      <div className="projects-grid">{projects.map(p => <article className={`project-card ${p.featured ? 'featured' : ''}`} key={p.title}>
        <h3>{p.title}</h3>{p.status && <span className="badge project-status">{p.status}</span>}{p.unavailable && <span className="badge warning">Temporarily Unavailable</span>}<p>{p.description}</p>{p.tech && <div className="project-tech" aria-label={`${p.title} technology stack`}>{p.tech.map(item => <span key={item}>{item}</span>)}</div>}{p.href && <a className="text-link" href={p.href} target={p.external ? '_blank' : undefined} rel={p.external ? 'noopener noreferrer' : undefined}>{p.linkLabel || 'Open interactive project'} →</a>}
      </article>)}</div>
    </section>
    <section className="contact" id="contact"><div><p className="eyebrow">Contact</p><h2>Let&apos;s build something useful with data.</h2></div><a className="button primary" href="mailto:ridho.trivonanda@gmail.com">ridho.trivonanda@gmail.com</a></section>
  </main><Footer /></div>;
}

function Card({ title, eyebrow, children, className = '' }) {
  return <section className={`ml-card ${className}`}>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2 className="card-title">{title}</h2>{children}</section>;
}

function FileUpload({ onUploaded, label = 'Upload dataset' }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [drag, setDrag] = useState(false);
  const input = useRef();
  const upload = async file => {
    setError('');
    if (!file) return;
    if (!/\.(csv|xlsx)$/i.test(file.name)) return setError('Choose a CSV or XLSX file.');
    if (!file.size) return setError('This file is empty.');
    if (file.size > MAX_FILE_SIZE) return setError('This file exceeds the 5 MB limit.');
    setBusy(true);
    try {
      const body = new FormData(); body.append('file', file);
      onUploaded(await api('/api/ml/upload', { method: 'POST', body }));
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  return <div>
    <div className={`dropzone ${drag ? 'dragging' : ''}`} tabIndex="0" role="button"
      onClick={() => input.current.click()} onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && input.current.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files[0]); }}>
      <span className="upload-icon">↑</span><strong>{busy ? 'Reading your dataset…' : label}</strong>
      <span>Drag and drop or choose a file</span><small>CSV or XLSX · maximum 5 MB · 10,000 rows · 50 columns</small>
      <input ref={input} type="file" accept=".csv,.xlsx" hidden onChange={e => upload(e.target.files[0])} />
    </div>
    {error && <p className="alert error" role="alert">{error}</p>}
  </div>;
}

function Stat({ label, value }) { return <div className="stat"><span>{label}</span><strong>{value}</strong></div>; }
function Field({ label, help, children }) { return <label className="field"><span>{label}{help && <span className="tooltip" title={help}>?</span>}</span>{children}</label>; }

function DatasetOverview({ data }) {
  const [page, setPage] = useState(0);
  const rows = data.preview.slice(page * 10, page * 10 + 10);
  return <Card eyebrow="Step 2" title="Preview & validate">
    <div className="stats-grid">
      <Stat label="File" value={data.file.name}/><Stat label="Size" value={data.file.size_display}/><Stat label="Rows" value={data.summary.rows.toLocaleString()}/>
      <Stat label="Columns" value={data.summary.columns}/><Stat label="Missing cells" value={data.summary.missing_values.toLocaleString()}/><Stat label="Duplicate rows" value={data.summary.duplicates.toLocaleString()}/>
    </div>
    <div className="type-pills">{['numeric','categorical','date','boolean','constant'].map(k => <span key={k}>{data.summary[`${k}_columns`]} {k}</span>)}</div>
    {data.sheets?.length > 1 && <p className="muted">Excel sheet: <strong>{data.active_sheet}</strong>. Re-upload a single-sheet export to choose a different sheet in this local version.</p>}
    <div className="table-wrap"><table><thead><tr>{data.columns.map(c => <th key={c.name} title={`${c.unique} unique · ${c.missing_pct}% missing`}>{c.name}<small>{c.dtype}</small></th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={i}>{data.columns.map(c => <td key={c.name}>{String(row[c.name] ?? '—')}</td>)}</tr>)}</tbody></table></div>
    <div className="pager"><button disabled={!page} onClick={() => setPage(p => p - 1)}>Previous</button><span>Preview rows {page * 10 + 1}–{Math.min(page * 10 + 10, data.preview.length)}</span><button disabled={(page + 1) * 10 >= data.preview.length} onClick={() => setPage(p => p + 1)}>Next</button></div>
    <details><summary>Column profile</summary><div className="table-wrap"><table><thead><tr><th>Column</th><th>Type</th><th>Unique</th><th>Missing</th><th>Examples</th></tr></thead><tbody>
      {data.columns.map(c => <tr key={c.name}><td>{c.name}{c.likely_id && <span className="badge warning">Likely ID</span>}</td><td>{c.dtype}</td><td>{c.unique}</td><td>{c.missing} ({c.missing_pct}%)</td><td>{c.examples.join(', ') || '—'}</td></tr>)}
    </tbody></table></div></details>
  </Card>;
}

const defaults = { test_size: .2, validation_size: .2, random_seed: 42, shuffle: true, stratify: true, numeric_missing: 'median', categorical_missing: 'most_frequent', encoding: 'onehot', scaling: 'none', date_handling: 'exclude', n_estimators: 300, learning_rate: .05, max_depth: 6, subsample: .8, colsample_bytree: .8, min_child_weight: 1, gamma: 0, reg_alpha: 0, reg_lambda: 1, tuning: 'none', iterations: 10, cv_folds: 3 };

function Builder({ data, onResult }) {
  const usable = data.columns.filter(c => c.dtype !== 'constant');
  const [target, setTarget] = useState('');
  const [features, setFeatures] = useState([]);
  const [problem, setProblem] = useState('');
  const [cfg, setCfg] = useState(defaults);
  const [advanced, setAdvanced] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const suggested = target ? data.columns.find(c => c.name === target)?.problem_suggestion : null;
  useEffect(() => { if (suggested) setProblem(suggested.type); }, [target]);
  useEffect(() => { setFeatures(usable.filter(c => c.name !== target && !c.likely_id).map(c => c.name)); }, [target]);
  const update = (key, value) => setCfg(c => ({ ...c, [key]: value }));
  const train = async () => {
    setError('');
    if (!target) return setError('Select a target column.');
    if (!features.length) return setError('Select at least one feature column.');
    try {
      const job = await api('/api/ml/train', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataset_id: data.dataset_id, target, features, problem_type: problem, config: cfg }) });
      setStatus({ job_id: job.job_id, state: 'queued', progress: 0 });
    } catch (e) { setError(e.message); }
  };
  useEffect(() => {
    if (!status?.job_id || ['completed','failed','cancelled'].includes(status.state)) return;
    const timer = setInterval(async () => {
      try {
        const next = await api(`/api/ml/train/${status.job_id}/status`); setStatus(next);
        if (next.state === 'completed') onResult(await api(`/api/ml/results/${status.job_id}`));
      } catch (e) { setError(e.message); }
    }, 800);
    return () => clearInterval(timer);
  }, [status?.job_id, status?.state]);
  const running = status && !['completed','failed','cancelled'].includes(status.state);
  return <div id="builder" className="builder-grid">
    <Card eyebrow="Step 3" title="Target & features">
      <Field label="Target column"><select value={target} onChange={e => setTarget(e.target.value)}><option value="">Select target…</option>{usable.map(c => <option key={c.name}>{c.name}</option>)}</select></Field>
      {suggested && <p className="suggestion"><strong>Suggested: {suggested.type.replace('_',' ')}</strong><br/>{suggested.reason}</p>}
      <Field label="Problem type"><select value={problem} onChange={e => setProblem(e.target.value)} disabled={!target}><option value="binary_classification">Binary classification</option><option value="multiclass_classification">Multiclass classification</option><option value="regression">Regression</option></select></Field>
      <div className="selector-head"><span>Feature columns ({features.length})</span><span><button className="link-button" onClick={() => setFeatures(usable.filter(c => c.name !== target).map(c => c.name))}>Select all</button><button className="link-button" onClick={() => setFeatures([])}>Clear</button></span></div>
      <div className="check-list">{usable.filter(c => c.name !== target).map(c => <label key={c.name}><input type="checkbox" checked={features.includes(c.name)} onChange={e => setFeatures(f => e.target.checked ? [...f,c.name] : f.filter(x => x !== c.name))}/><span>{c.name}{c.likely_id && <em>Likely ID</em>}</span></label>)}</div>
      {features.some(f => data.columns.find(c => c.name === f)?.likely_id) && <p className="alert warning">Likely identifier columns are included. They can encourage memorization and poor real-world performance.</p>}
    </Card>
    <Card eyebrow="Steps 4–6" title="Configure model">
      <div className="form-grid">
        <Field label="Numeric missing"><select value={cfg.numeric_missing} onChange={e=>update('numeric_missing',e.target.value)}><option value="median">Median</option><option value="mean">Mean</option><option value="zero">Zero</option><option value="drop">Drop rows</option></select></Field>
        <Field label="Categorical missing"><select value={cfg.categorical_missing} onChange={e=>update('categorical_missing',e.target.value)}><option value="most_frequent">Most frequent</option><option value="constant">Unknown</option><option value="drop">Drop rows</option></select></Field>
        <Field label="Categorical encoding"><select value={cfg.encoding} onChange={e=>update('encoding',e.target.value)}><option value="onehot">One-hot</option><option value="ordinal">Ordinal</option></select></Field>
        <Field label="Numeric scaling" help="Tree models usually do not need scaling."><select value={cfg.scaling} onChange={e=>update('scaling',e.target.value)}><option value="none">No scaling</option><option value="standard">Standard</option><option value="minmax">Min-max</option></select></Field>
        <Field label="Test size"><input type="number" min=".1" max=".4" step=".05" value={cfg.test_size} onChange={e=>update('test_size',+e.target.value)}/></Field>
        <Field label="Random seed"><input type="number" value={cfg.random_seed} onChange={e=>update('random_seed',+e.target.value)}/></Field>
      </div>
      <div className="inline-checks"><label><input type="checkbox" checked={cfg.shuffle} onChange={e=>update('shuffle',e.target.checked)}/> Shuffle</label><label><input type="checkbox" checked={cfg.stratify} onChange={e=>update('stratify',e.target.checked)}/> Stratify classification</label></div>
      <h3 className="subheading">XGBoost essentials</h3><div className="form-grid">
        {[['n_estimators',100,1000,50],['learning_rate',.01,.3,.01],['max_depth',2,12,1],['subsample',.5,1,.05],['colsample_bytree',.5,1,.05],['min_child_weight',1,10,1]].map(([k,min,max,step]) => <Field key={k} label={k.replaceAll('_',' ')}><input type="number" min={min} max={max} step={step} value={cfg[k]} onChange={e=>update(k,+e.target.value)}/></Field>)}
      </div>
      <details open={advanced} onToggle={e=>setAdvanced(e.currentTarget.open)}><summary>Advanced parameters & tuning</summary>
        <div className="form-grid">{[['gamma',0,10,.1],['reg_alpha',0,10,.1],['reg_lambda',.1,20,.1]].map(([k,min,max,step]) => <Field key={k} label={k.replace('_',' ')}><input type="number" min={min} max={max} step={step} value={cfg[k]} onChange={e=>update(k,+e.target.value)}/></Field>)}
          <Field label="Tuning method"><select value={cfg.tuning} onChange={e=>update('tuning',e.target.value)}><option value="none">No tuning</option><option value="random">Randomized search</option><option value="grid">Compact grid search</option></select></Field>
          {cfg.tuning !== 'none' && <><Field label="Iterations / trials"><input type="number" min="2" max="30" value={cfg.iterations} onChange={e=>update('iterations',+e.target.value)}/></Field><Field label="CV folds"><input type="number" min="2" max="5" value={cfg.cv_folds} onChange={e=>update('cv_folds',+e.target.value)}/></Field></>}
        </div>
        {cfg.tuning !== 'none' && <p className="workload">Estimated workload: <strong>{cfg.iterations * cfg.cv_folds > 40 ? 'Heavy' : cfg.iterations * cfg.cv_folds > 15 ? 'Medium' : 'Light'}</strong> · capped at 30 trials</p>}
      </details>
      <div className="actions"><button className="button secondary compact" onClick={()=>setCfg(defaults)}>Reset defaults</button><button className="button primary compact" disabled={running} onClick={train}>{running ? 'Training…' : 'Train model'}</button></div>
      {error && <p className="alert error">{error}</p>}
      {status && <TrainingStatus status={status} onCancel={async()=>{ await api(`/api/ml/train/${status.job_id}/cancel`,{method:'POST'}); setStatus(s=>({...s,state:'cancelled'})); }}/>}
    </Card>
  </div>;
}

function TrainingStatus({ status, onCancel }) {
  const active = !['completed','failed','cancelled'].includes(status.state);
  return <div className="training"><div><span className={`status-dot ${status.state}`}/><strong>{status.state.replace('_',' ')}</strong><span>{status.message}</span></div><progress max="100" value={status.progress || 0}/>{active && <button onClick={onCancel}>Cancel</button>}{status.error && <p className="alert error">{status.error}</p>}</div>;
}

function BarChart({ items }) {
  const max = Math.max(...items.map(x => x.importance), .0001);
  return <div className="bar-chart" aria-label="Feature importance chart">{items.slice(0,15).map(x => <div className="bar-row" key={x.feature}><span title={x.feature}>{x.feature}</span><div><i style={{width:`${x.importance/max*100}%`}}/><small>{x.importance.toFixed(3)}</small></div></div>)}</div>;
}

function Results({ result }) {
  const metrics = Object.entries(result.metrics).filter(([,v]) => typeof v === 'number');
  return <div id="results" className="results-stack">
    <Card eyebrow="Completed" title="Model evaluation"><p className="success-copy">{result.interpretation}</p><div className="metric-grid">{metrics.map(([k,v])=><Stat key={k} label={k.replaceAll('_',' ')} value={v.toFixed(4)}/>)}</div>
      {result.warnings?.map(w=><p className="alert warning" key={w}>{w}</p>)}
    </Card>
    <div className="builder-grid"><Card title="Feature importance"><BarChart items={result.feature_importance}/></Card>
      <Card title="Model summary"><dl className="summary-list">{Object.entries(result.summary).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd></div>)}</dl></Card></div>
    <Card title="Unseen test predictions"><div className="download-row"><a className="button secondary compact" href={`${API}/api/ml/download/${result.job_id}/predictions`}>Predictions CSV</a><a className="button secondary compact" href={`${API}/api/ml/download/${result.job_id}/metrics`}>Metrics JSON</a><a className="button secondary compact" href={`${API}/api/ml/download/${result.job_id}/model`}>Trusted model file</a></div>
      <p className="muted">Only load serialized model files from sources you trust.</p><div className="table-wrap"><table><thead><tr>{Object.keys(result.predictions[0]||{}).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{result.predictions.slice(0,25).map((r,i)=><tr key={i}>{Object.values(r).map((v,j)=><td key={j}>{String(v)}</td>)}</tr>)}</tbody></table></div>
    </Card>
    <Card title="Predict new data"><p className="muted">Upload data with the same feature columns. Extra columns are preserved; missing required columns are rejected.</p><NewPrediction jobId={result.job_id}/></Card>
  </div>;
}

function NewPrediction({ jobId }) {
  const [result,setResult]=useState(null), [error,setError]=useState('');
  const upload = async e => { const file=e.target.files[0]; if(!file)return; setError(''); const body=new FormData();body.append('file',file);try{setResult(await api(`/api/ml/predict/${jobId}`,{method:'POST',body}));}catch(x){setError(x.message);} };
  return <div><input className="file-input" type="file" accept=".csv,.xlsx,.xls" onChange={upload}/>{error&&<p className="alert error">{error}</p>}{result&&<><p className="alert success">{result.rows} predictions created.</p><a className="button primary compact" href={`${API}/api/ml/download/${jobId}/new-predictions`}>Download new predictions</a></>}</div>;
}

export function XGBoostPage() {
  const [data,setData]=useState(null), [result,setResult]=useState(null);
  if (!XGBOOST_ENABLED) return <div className="site"><Header/><main className="ml-main"><section className="ml-hero"><div><p className="eyebrow">Interactive machine learning lab</p><h1>XGBoost Model Builder</h1><p>This project is temporarily unavailable while resource controls are being improved. Explore the EDA or Customer 360 projects from the portfolio.</p><a className="button primary compact" href="/">Back to portfolio</a></div></section></main><Footer/></div>;
  return <div className="site"><Header app/><main className="ml-main">
    <section className="ml-hero"><div><p className="eyebrow">Interactive machine learning lab</p><h1>XGBoost Model Builder</h1><p>Move from a raw spreadsheet to a validated, reusable XGBoost pipeline—without pretending browser-side training is enough.</p></div><div className="step-list">{['Upload','Inspect','Configure','Train','Evaluate'].map((s,i)=><span className={data && i<2 ? 'done':''} key={s}><b>{i+1}</b>{s}</span>)}</div></section>
    <p className="privacy-note">Privacy notice: uploaded data is processed by this application. Do not upload confidential data unless this deployment is private and secure.</p>
    <Card eyebrow="Step 1" title="Upload a dataset"><FileUpload onUploaded={d=>{setData(d);setResult(null);}}/></Card>
    {data&&<><DatasetOverview data={data}/><Builder data={data} onResult={setResult}/></>}
    {result&&<Results result={result}/>}
  </main><Footer/></div>;
}

import React, { useEffect, useState } from 'react';
import { datasetsApi } from '../../api/datasets';
import { DatasetPreview } from './DatasetPreview';
import { FileUpload } from './FileUpload';
import { ErrorState } from '../ui/ErrorState';
import { LoadingState } from '../ui/LoadingState';
import { MetricCard } from '../ui/MetricCard';

export function DatasetWorkspace({ onDataset }) {
  const [dataset, setDataset] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mode, setMode] = useState('first');
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');

  async function upload(file) {
    setBusy(true); setError(''); setProgress(0);
    try {
      if (dataset) {
        await datasetsApi.remove(dataset.dataset_id).catch(() => {});
        setDataset(null); setPreview(null); onDataset?.(null);
      }
      const result = await datasetsApi.upload(file, setProgress);
      setDataset(result); setPreview({ rows: result.preview, offset: 0 });
      setMode('first'); setOffset(0); onDataset?.(result);
    } catch (uploadError) { setError(uploadError.message); }
    finally { setBusy(false); }
  }

  async function loadPreview(nextMode = mode, nextOffset = offset, nextLimit = limit) {
    if (!dataset) return;
    setBusy(true); setError('');
    try { setPreview(await datasetsApi.preview(dataset.dataset_id, { mode: nextMode, offset: nextOffset, limit: nextLimit })); }
    catch (previewError) {
      if (previewError.status === 404) {
        setDataset(null); setPreview(null); onDataset?.(null);
        setError('This dataset session expired. Please upload the file again.');
      } else setError(previewError.message);
    }
    finally { setBusy(false); }
  }

  async function changeSheet(sheet) {
    setBusy(true); setError('');
    try {
      const result = await datasetsApi.selectSheet(dataset.dataset_id, sheet);
      setDataset(result); setPreview({ rows: result.preview, offset: 0 }); setOffset(0); onDataset?.(result);
    } catch (sheetError) { setError(sheetError.message); }
    finally { setBusy(false); }
  }

  async function clear() {
    if (dataset) await datasetsApi.remove(dataset.dataset_id).catch(() => {});
    setDataset(null); setPreview(null); setError(''); setProgress(0); onDataset?.(null);
  }

  useEffect(() => () => {
    if (dataset?.dataset_id) datasetsApi.remove(dataset.dataset_id).catch(() => {});
  }, [dataset?.dataset_id]);

  if (!dataset) return <>
    <FileUpload onSelect={upload} busy={busy} />
    {busy && <><progress className="upload-progress" max="100" value={progress} /><LoadingState label={progress < 100 ? `Uploading… ${progress}%` : 'Validating and profiling…'} /></>}
    {error && <ErrorState message={error} />}
  </>;

  const summary = dataset.summary;
  return <div>
    <div className="dataset-file-row"><div><strong>{dataset.file.name}</strong><span>{dataset.file.size_display} · expires after {Math.round(dataset.expires_in_seconds / 60)} inactive minutes</span></div><button onClick={clear}>Clear & replace</button></div>
    {dataset.sheets?.length > 1 && <label className="sheet-selector">Worksheet<select value={dataset.active_sheet} onChange={(event) => changeSheet(event.target.value)}>{dataset.sheets.map((sheet) => <option key={sheet}>{sheet}</option>)}</select></label>}
    <div className="stats-grid dataset-stats">
      <MetricCard label="Rows" value={summary.rows.toLocaleString()} />
      <MetricCard label="Columns" value={summary.columns} />
      <MetricCard label="Missing cells" value={summary.missing_values.toLocaleString()} />
      <MetricCard label="Duplicates" value={summary.duplicates.toLocaleString()} />
      <MetricCard label="Numeric" value={summary.numeric_columns} />
      <MetricCard label="Categorical" value={summary.categorical_columns} />
    </div>
    {busy && <LoadingState label="Loading dataset preview…" />}
    {error && <ErrorState message={error} onRetry={() => loadPreview()} />}
    <DatasetPreview dataset={dataset} preview={preview} mode={mode} limit={limit}
      onMode={(value) => { setMode(value); setOffset(0); loadPreview(value, 0, limit); }}
      onLimit={(value) => { setLimit(value); setOffset(0); loadPreview(mode, 0, value); }}
      onPage={(value) => { setOffset(value); loadPreview(mode, value, limit); }} />
  </div>;
}

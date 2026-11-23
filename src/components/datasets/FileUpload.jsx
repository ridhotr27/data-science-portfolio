import React, { useRef, useState } from 'react';

const MAX_FILE_SIZE = 5 * 1024 * 1024;

export function FileUpload({ onSelect, busy = false, accept = '.csv,.xlsx', maxBytes = MAX_FILE_SIZE }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');

  function select(file) {
    setError('');
    if (!file) return;
    if (!/\.(csv|xlsx)$/i.test(file.name)) {
      setError('Choose a CSV or XLSX file.');
      return;
    }
    if (!file.size) {
      setError('This file is empty.');
      return;
    }
    if (file.size > maxBytes) {
      setError(`This file exceeds the ${Math.round(maxBytes / 1024 / 1024)} MB limit.`);
      return;
    }
    onSelect(file);
  }

  return (
    <div>
      <div className={`dropzone ${dragging ? 'dragging' : ''}`} role="button" tabIndex="0"
        aria-label="Upload a CSV or XLSX dataset"
        onClick={() => input.current?.click()}
        onKeyDown={(event) => ['Enter', ' '].includes(event.key) && input.current?.click()}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); select(event.dataTransfer.files[0]); }}>
        <span className="upload-icon">↑</span>
        <strong>{busy ? 'Uploading your dataset…' : 'Upload a dataset'}</strong>
        <span>Drag and drop or choose a file</span>
        <small>CSV or XLSX · maximum {Math.round(maxBytes / 1024 / 1024)} MB · 10,000 rows · 50 columns</small>
        <input ref={input} type="file" accept={accept} hidden onChange={(event) => select(event.target.files[0])} />
      </div>
      {error && <p className="alert error" role="alert">{error}</p>}
    </div>
  );
}

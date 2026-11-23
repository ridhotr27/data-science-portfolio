import { request, uploadRequest } from './client';

export const datasetsApi = {
  upload: (file, onProgress) => uploadRequest('/api/datasets/upload', file, onProgress),
  preview: (id, { mode = 'first', offset = 0, limit = 25 } = {}) =>
    request(`/api/datasets/${id}/preview?mode=${mode}&offset=${offset}&limit=${limit}`),
  schema: (id) => request(`/api/datasets/${id}/schema`),
  selectSheet: (id, sheet) => request(`/api/datasets/${id}/sheet`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sheet }),
  }),
  remove: (id) => request(`/api/datasets/${id}`, { method: 'DELETE' }),
};

import { downloadRequest, request } from './client';

const json = (body) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const edaApi = {
  overview: (id) => request(`/api/eda/${id}/overview`),
  profile: (id, overrides = {}, columns = null) =>
    request(`/api/eda/${id}/profile`, json({ overrides, columns })),
  quality: (id, overrides = {}) =>
    request(`/api/eda/${id}/quality`, json({ overrides })),
  distribution: (id, body) => request(`/api/eda/${id}/distribution`, json(body)),
  correlation: (id, body) => request(`/api/eda/${id}/correlation`, json(body)),
  relationship: (id, body) => request(`/api/eda/${id}/relationship`, json(body)),
  outliers: (id, body) => request(`/api/eda/${id}/outliers`, json(body)),
  target: (id, body) => request(`/api/eda/${id}/target-analysis`, json(body)),
  readiness: (id, body) => request(`/api/eda/${id}/readiness`, json(body)),
  insights: (id, overrides = {}) => request(`/api/eda/${id}/insights`, json({ overrides })),
  export: (id, body, filename) => downloadRequest(`/api/eda/${id}/export`, body, filename),
};

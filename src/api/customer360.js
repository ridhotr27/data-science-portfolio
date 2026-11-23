import { downloadRequest, request } from './client';

const json = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
export const customer360Api = {
  suggestions: (id) => request(`/api/customer-360/${id}/suggestions`),
  configure: (id, mapping) => request(`/api/customer-360/${id}/configure`, json(mapping)),
  overview: (id, query) => request(`/api/customer-360/${id}/overview`, json(query)),
  revenue: (id, query) => request(`/api/customer-360/${id}/revenue`, json(query)),
  rfm: (id, query) => request(`/api/customer-360/${id}/rfm`, json(query)),
  cohorts: (id, query) => request(`/api/customer-360/${id}/cohorts`, json(query)),
  behavior: (id, query) => request(`/api/customer-360/${id}/behavior`, json(query)),
  customers: (id, query) => request(`/api/customer-360/${id}/customers`, json(query)),
  customer: (id, customerId) => request(`/api/customer-360/${id}/customers/${encodeURIComponent(customerId)}`),
  insights: (id, query) => request(`/api/customer-360/${id}/insights`, json(query)),
  export: (id, body, filename) => downloadRequest(`/api/customer-360/${id}/export`, body, filename),
};

import React, { Suspense, lazy } from 'react';
import { PortfolioPage, XGBoostPage } from '../pages/LegacyPages';
import { LoadingState } from '../components/ui/LoadingState';

const Customer360Page = lazy(() => import('../pages/Customer360Page').then((module) => ({ default: module.Customer360Page })));
const EdaPage = lazy(() => import('../pages/EdaPage').then((module) => ({ default: module.EdaPage })));

const routes = {
  '/': PortfolioPage,
  '/projects/xgboost-predictor': XGBoostPage,
  '/projects/customer-360': Customer360Page,
  '/projects/exploratory-data-analysis': EdaPage,
};

export function App() {
  const path = window.location.pathname.replace(/\/$/, '') || '/';
  const Page = routes[path] || PortfolioPage;
  return <Suspense fallback={<main className="ml-main"><LoadingState label="Loading analytics workspace…" /></main>}><Page /></Suspense>;
}

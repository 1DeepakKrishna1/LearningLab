import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import HomePage from './pages/HomePage';
import DatasetsPage from './pages/DatasetsPage';
import QueryPage from './pages/QueryPage';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="query" element={<QueryPage />} />
        <Route path="dashboards" element={<DashboardPage />} />
        <Route path="dashboards/:id" element={<DashboardPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
};

export default App;

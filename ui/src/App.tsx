import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { Layout } from '@/components/layout/Layout';
import { Login } from '@/pages/auth/Login';
import { RouteList } from '@/pages/routes/RouteList';
import { RouteEditor } from '@/pages/routes/RouteEditor';
import { RouteDetail } from '@/pages/routes/RouteDetail';
import { RouteTester } from '@/pages/routes/RouteTester';
import { SystemStatus } from '@/pages/system/SystemStatus';
import { AuthManagement } from '@/pages/auth/AuthManagement';
import { Settings } from '@/pages/Settings';

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

// Main app routes
function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/routes" replace />} />
        <Route path="routes" element={<RouteList />} />
        <Route path="routes/new" element={<RouteEditor />} />
        <Route path="routes/:id" element={<RouteDetail />} />
        <Route path="routes/:id/edit" element={<RouteEditor />} />
        <Route path="routes/:id/test" element={<RouteTester />} />
        <Route path="system" element={<SystemStatus />} />
        <Route path="auth" element={<AuthManagement />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/routes" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="App">
          <AppRoutes />
        </div>
      </AuthProvider>
    </Router>
  );
}
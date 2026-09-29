import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";

const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Complaints = lazy(() => import("./pages/Complaints"));
const Predictions = lazy(() => import("./pages/Predictions"));
const Intelligence = lazy(() => import("./pages/Intelligence"));
const Alerts = lazy(() => import("./pages/Alerts"));
const GraphPage = lazy(() => import("./pages/GraphPage"));

function Protected({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Suspense fallback={<div className="grid min-h-screen place-items-center bg-bg text-sm font-medium text-muted">Loading VIZHI…</div>}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Protected><Dashboard /></Protected>} />
        <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
        <Route path="/complaints" element={<Protected><Complaints /></Protected>} />
        <Route path="/predictions" element={<Protected><Predictions /></Protected>} />
        <Route path="/intelligence" element={<Protected><Intelligence /></Protected>} />
        <Route path="/alerts" element={<Protected><Alerts /></Protected>} />
        <Route path="/graph" element={<Protected><GraphPage /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

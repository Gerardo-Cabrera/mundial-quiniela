import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ErrorBoundary } from "react-error-boundary";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { useInactivityLogout } from "@/hooks";
import { Navbar } from "@/components/Navbar";
import { ErrorFallback } from "@/components/ErrorFallback";
import { TOASTER_STYLE } from "@/config";

import LoginPage          from "@/pages/Login";
import ChangePasswordPage from "@/pages/ChangePassword";
import Dashboard          from "@/pages/Dashboard";
import MatchesPage        from "@/pages/Matches";
import ResultsPage        from "@/pages/Results";
import MyPredictionsPage  from "@/pages/MyPredictions";
import JornadaPage        from "@/pages/Jornada";
import MvpsPage           from "@/pages/Mvps";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function ProtectedLayout() {
  const { isAuthenticated, user } = useAuthStore();
  useInactivityLogout();  // cierra la sesión tras 1 h de inactividad
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  // Primer ingreso: obligar a cambiar la contraseña inicial antes de usar la app.
  if (user?.must_change_password) return <ChangePasswordPage forced />;

  return (
    <div className="min-h-screen ucl-stars-bg">
      <Navbar />
      <main className="lg:pl-56 pt-14 pb-20 lg:pt-0 lg:pb-0">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/"                element={<Dashboard />} />
            <Route path="/matches"         element={<MatchesPage />} />
            <Route path="/results"         element={<ResultsPage />} />
            <Route path="/matchdays"       element={<JornadaPage />} />
            <Route path="/mvps"            element={<MvpsPage />} />
            <Route path="/predictions"     element={<MyPredictionsPage />} />
            <Route path="/change-password" element={<ChangePasswordPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/*"     element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{ style: TOASTER_STYLE }}
        />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

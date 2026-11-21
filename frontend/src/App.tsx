import { useEffect } from "react";
import { TopBar } from "./components/layout/TopBar";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { useHashRoute } from "./lib/useHashRoute";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { WorkspacePage } from "./pages/WorkspacePage";

/** Decides what to show: account pages when signed out, the app when signed in. */
function Routes() {
  const { user } = useAuth();
  const { route, openProject, openPage } = useHashRoute();
  const isAccountPage = route.page === "login" || route.page === "signup";

  // Route guard: signed-out users only see login/signup; signed-in users skip them.
  useEffect(() => {
    if (!user && !isAccountPage) openPage("login");
    if (user && isAccountPage) openPage("dashboard");
  }, [user, isAccountPage, openPage]);

  if (!user) {
    if (route.page === "signup") {
      return <SignupPage onSignedIn={() => openPage("dashboard")} onLogin={() => openPage("login")} />;
    }
    return <LoginPage onSignedIn={() => openPage("dashboard")} onSignup={() => openPage("signup")} />;
  }

  return (
    <div className="shell">
      <TopBar page={route.page} onNavigate={openPage} />
      {route.page === "projects" || route.page === "project" ? (
        <WorkspacePage route={route} onOpenProject={openProject} />
      ) : (
        <DashboardPage onOpenProject={openProject} />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Routes />
      </ToastProvider>
    </AuthProvider>
  );
}

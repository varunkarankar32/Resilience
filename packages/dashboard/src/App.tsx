import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Incidents from "./pages/Incidents";
import IncidentDetail from "./pages/IncidentDetail";
import { useAuth } from "./hooks/useAuth";
import { useSocketCleanup } from "./hooks/useSocket";

function App() {
  const { auth, loading, login, logout } = useAuth();
  useSocketCleanup();

  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <Link to="/" className="navbar-brand">
            ResilienceAI
          </Link>
          <div className="navbar-links">
            <Link to="/">Dashboard</Link>
            <Link to="/incidents">Incidents</Link>
          </div>
          <div className="navbar-auth">
            {loading ? (
              <span>Loading...</span>
            ) : auth ? (
              <>
                <span>{auth.user.name}</span>
                <button onClick={logout} className="btn btn-secondary">
                  Logout
                </button>
              </>
            ) : (
              <span>Phase 4: Auth</span>
            )}
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Incidents />} />
            <Route path="/incidents" element={<Incidents />} />
            <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import TargetConfig from "./pages/TargetConfig";
import Evaluation from "./pages/Evaluation";
import History from "./pages/History"
import RedTeam from "./pages/RedTeam"
import Vulnerabilities from "./pages/Vulnerabilities"
import Hardening from "./pages/Hardening"
const links = [
  ["/", "Dashboard"],
  ["/target", "Target AI Config"],
  ["/evaluation", "Evaluation"],
  ["/history", "History"],
  ["/redteam", "Red-Team Testing"],
  ["/vulnerabilities", "Vulnerabilities"],
  ["/hardening", "Prompt Hardening"],
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <nav className="sidebar">
          <div className="brand">PROMPTSHIELD</div>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/target" element={<TargetConfig />} />
                        <Route path="/evaluation" element={<Evaluation />} />
                        <Route path="/history" element={<History />} />
                        <Route path="/redteam" element={<RedTeam />} />
                        <Route path="/vulnerabilities" element={<Vulnerabilities />} />
                        <Route path="/hardening" element={<Hardening />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import TargetConfig from "./pages/TargetConfig";

const links = [
  ["/", "Dashboard"],
  ["/target", "Target AI Config"],
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
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
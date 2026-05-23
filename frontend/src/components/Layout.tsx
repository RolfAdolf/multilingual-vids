import { NavLink, Outlet } from "react-router-dom";

const NAV: { to: string; label: string; end?: boolean }[] = [
  { to: "/", label: "New Job", end: true },
  { to: "/jobs", label: "Jobs" },
  { to: "/models", label: "Models & Coverage" },
];

export function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__logo">VT</span>
          <div>
            <strong>VT STUDIO</strong>
            <span>Video Translation Studio</span>
          </div>
        </div>
        <nav className="sidebar__nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                `sidebar__link${isActive ? " sidebar__link--active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <footer className="sidebar__footer">
          <p className="sidebar__plan">Multilingual Videos · MVP</p>
          <p className="sidebar__hint">Polling status every 3s · Max 500 MB</p>
        </footer>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

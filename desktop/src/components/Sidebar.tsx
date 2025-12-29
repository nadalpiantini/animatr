import { NavLink } from "react-router-dom";
import { useStore } from "../hooks/useStore";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: "home" },
  { path: "/projects", label: "Proyectos", icon: "folder" },
  { path: "/editor", label: "Editor", icon: "edit" },
  { path: "/render", label: "Render", icon: "play" },
  { path: "/settings", label: "Ajustes", icon: "settings" },
];

function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, dependencies } = useStore();

  return (
    <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        <h1 className="logo">
          {sidebarCollapsed ? "A" : "ANIMATR"}
        </h1>
        <button className="collapse-btn" onClick={toggleSidebar}>
          {sidebarCollapsed ? ">" : "<"}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? "active" : ""}`
            }
          >
            <span className={`icon icon-${item.icon}`}></span>
            {!sidebarCollapsed && <span className="label">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="status-indicators">
          <StatusDot ok={dependencies.python} label="Python" collapsed={sidebarCollapsed} />
          <StatusDot ok={dependencies.moho} label="Moho" collapsed={sidebarCollapsed} />
          <StatusDot ok={dependencies.blender} label="Blender" collapsed={sidebarCollapsed} />
          <StatusDot ok={dependencies.ffmpeg} label="FFmpeg" collapsed={sidebarCollapsed} />
        </div>
      </div>
    </aside>
  );
}

function StatusDot({ ok, label, collapsed }: { ok: boolean; label: string; collapsed: boolean }) {
  return (
    <div className="status-dot" title={`${label}: ${ok ? "OK" : "No disponible"}`}>
      <span className={`dot ${ok ? "ok" : "error"}`}></span>
      {!collapsed && <span className="status-label">{label}</span>}
    </div>
  );
}

export default Sidebar;

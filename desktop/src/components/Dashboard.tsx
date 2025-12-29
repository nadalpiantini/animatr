import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import { useStore } from "../hooks/useStore";

interface Stats {
  totalProjects: number;
  activeRenders: number;
  completedToday: number;
}

function Dashboard() {
  const navigate = useNavigate();
  const { projects, setProjects, dependencies } = useStore();
  const [stats, setStats] = useState<Stats>({
    totalProjects: 0,
    activeRenders: 0,
    completedToday: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const projectList = await invoke<any[]>("list_projects");
      setProjects(projectList);
      setStats({
        totalProjects: projectList.length,
        activeRenders: projectList.filter((p) => p.status === "rendering").length,
        completedToday: projectList.filter((p) => {
          const created = new Date(p.createdAt);
          const today = new Date();
          return created.toDateString() === today.toDateString();
        }).length,
      });
    } catch (error) {
      console.error("Failed to load dashboard:", error);
    } finally {
      setLoading(false);
    }
  }

  const missingDeps = Object.entries(dependencies)
    .filter(([_, ok]) => !ok)
    .map(([name]) => name);

  return (
    <div className="dashboard">
      <header className="page-header">
        <h1>Dashboard</h1>
        <button className="btn btn-primary" onClick={() => navigate("/projects")}>
          + Nuevo Proyecto
        </button>
      </header>

      {missingDeps.length > 0 && (
        <div className="alert alert-warning">
          <strong>Dependencias faltantes:</strong> {missingDeps.join(", ")}
          <p>Algunas funcionalidades pueden no estar disponibles.</p>
        </div>
      )}

      <div className="stats-grid">
        <StatCard
          title="Proyectos Totales"
          value={stats.totalProjects}
          icon="folder"
        />
        <StatCard
          title="Renders Activos"
          value={stats.activeRenders}
          icon="play"
          variant={stats.activeRenders > 0 ? "active" : undefined}
        />
        <StatCard
          title="Completados Hoy"
          value={stats.completedToday}
          icon="check"
        />
      </div>

      <section className="recent-projects">
        <h2>Proyectos Recientes</h2>
        {loading ? (
          <div className="loading">Cargando...</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            <p>No hay proyectos aun.</p>
            <button
              className="btn btn-secondary"
              onClick={() => navigate("/projects")}
            >
              Crear tu primer proyecto
            </button>
          </div>
        ) : (
          <div className="project-list">
            {projects.slice(0, 5).map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={() => navigate(`/editor/${project.id}`)}
              />
            ))}
          </div>
        )}
      </section>

      <section className="quick-actions">
        <h2>Acciones Rapidas</h2>
        <div className="action-grid">
          <ActionCard
            title="Generar con IA"
            description="Crea un video desde un prompt"
            icon="ai"
            onClick={() => navigate("/editor?mode=ai")}
          />
          <ActionCard
            title="Importar YAML"
            description="Carga un spec existente"
            icon="import"
            onClick={() => navigate("/editor?mode=import")}
          />
          <ActionCard
            title="Ver Renders"
            description="Historial de renderizados"
            icon="history"
            onClick={() => navigate("/render")}
          />
        </div>
      </section>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  variant,
}: {
  title: string;
  value: number;
  icon: string;
  variant?: string;
}) {
  return (
    <div className={`stat-card ${variant || ""}`}>
      <span className={`icon icon-${icon}`}></span>
      <div className="stat-content">
        <span className="stat-value">{value}</span>
        <span className="stat-title">{title}</span>
      </div>
    </div>
  );
}

function ProjectCard({ project, onClick }: { project: any; onClick: () => void }) {
  return (
    <div className="project-card" onClick={onClick}>
      <div className="project-info">
        <h3>{project.name}</h3>
        <p>{project.description || "Sin descripcion"}</p>
      </div>
      <div className="project-meta">
        <span className={`status status-${project.status}`}>{project.status}</span>
      </div>
    </div>
  );
}

function ActionCard({
  title,
  description,
  icon,
  onClick,
}: {
  title: string;
  description: string;
  icon: string;
  onClick: () => void;
}) {
  return (
    <div className="action-card" onClick={onClick}>
      <span className={`icon icon-${icon}`}></span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

export default Dashboard;

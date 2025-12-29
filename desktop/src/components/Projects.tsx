import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import { useStore } from "../hooks/useStore";

function Projects() {
  const navigate = useNavigate();
  const { projects, setProjects, addProject } = useStore();
  const [loading, setLoading] = useState(true);
  const [showNewModal, setShowNewModal] = useState(false);
  const [newProject, setNewProject] = useState({ name: "", description: "" });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      const projectList = await invoke<any[]>("list_projects");
      setProjects(projectList);
    } catch (err) {
      console.error("Failed to load projects:", err);
      setError("Error al cargar proyectos");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newProject.name.trim()) return;

    setCreating(true);
    setError(null);

    try {
      const project = await invoke<any>("create_project", {
        name: newProject.name,
        description: newProject.description,
      });
      addProject(project);
      setShowNewModal(false);
      setNewProject({ name: "", description: "" });
      navigate(`/editor/${project.id}`);
    } catch (err) {
      console.error("Failed to create project:", err);
      setError("Error al crear proyecto");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="projects-page">
      <header className="page-header">
        <h1>Proyectos</h1>
        <button className="btn btn-primary" onClick={() => setShowNewModal(true)}>
          + Nuevo Proyecto
        </button>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-container">
          <div className="loader"></div>
          <p>Cargando proyectos...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📁</div>
          <h2>No hay proyectos</h2>
          <p>Crea tu primer proyecto de animacion</p>
          <button className="btn btn-primary" onClick={() => setShowNewModal(true)}>
            Crear Proyecto
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map((project) => (
            <div
              key={project.id}
              className="project-card"
              onClick={() => navigate(`/editor/${project.id}`)}
            >
              <div className="project-thumbnail">
                <span className="placeholder-icon">🎬</span>
              </div>
              <div className="project-details">
                <h3>{project.name}</h3>
                <p>{project.description || "Sin descripcion"}</p>
                <div className="project-footer">
                  <span className={`status status-${project.status}`}>
                    {project.status}
                  </span>
                  <span className="date">
                    {new Date(project.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNewModal && (
        <div className="modal-overlay" onClick={() => setShowNewModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Nuevo Proyecto</h2>
            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label htmlFor="name">Nombre</label>
                <input
                  id="name"
                  type="text"
                  value={newProject.name}
                  onChange={(e) =>
                    setNewProject({ ...newProject, name: e.target.value })
                  }
                  placeholder="Mi Video Animado"
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label htmlFor="description">Descripcion</label>
                <textarea
                  id="description"
                  value={newProject.description}
                  onChange={(e) =>
                    setNewProject({ ...newProject, description: e.target.value })
                  }
                  placeholder="Descripcion del proyecto..."
                  rows={3}
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowNewModal(false)}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={creating || !newProject.name.trim()}
                >
                  {creating ? "Creando..." : "Crear"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Projects;

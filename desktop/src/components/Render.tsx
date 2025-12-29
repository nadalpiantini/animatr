import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useStore } from "../hooks/useStore";

interface RenderJob {
  id: number;
  projectId: number;
  status: string;
  progress: number;
  currentScene?: string;
  outputPath?: string;
  errorMessage?: string;
  createdAt: string;
}

function Render() {
  const { activeRenderJob, setActiveRenderJob, renderHistory, addToRenderHistory } = useStore();
  const [jobs, setJobs] = useState<RenderJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRenderHistory();
  }, []);

  useEffect(() => {
    // Poll for active job status
    if (activeRenderJob && activeRenderJob.status === "processing") {
      const interval = setInterval(checkRenderStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [activeRenderJob]);

  async function loadRenderHistory() {
    try {
      // In production, this would call the backend
      setJobs([]);
    } catch (err) {
      console.error("Failed to load render history:", err);
    } finally {
      setLoading(false);
    }
  }

  async function checkRenderStatus() {
    if (!activeRenderJob) return;

    try {
      const status = await invoke<RenderJob>("get_render_status", {
        jobId: activeRenderJob.id,
      });

      setActiveRenderJob(status);

      if (status.status === "completed" || status.status === "failed") {
        addToRenderHistory(status);
        loadRenderHistory();
      }
    } catch (err) {
      console.error("Failed to check status:", err);
    }
  }

  async function handleCancelRender(jobId: number) {
    try {
      await invoke("cancel_render", { jobId });
      if (activeRenderJob?.id === jobId) {
        setActiveRenderJob(null);
      }
      loadRenderHistory();
    } catch (err) {
      console.error("Failed to cancel render:", err);
    }
  }

  return (
    <div className="render-page">
      <header className="page-header">
        <h1>Render</h1>
      </header>

      {activeRenderJob && activeRenderJob.status === "processing" && (
        <div className="active-render">
          <h2>Renderizado en Progreso</h2>
          <div className="render-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${activeRenderJob.progress * 100}%` }}
              />
            </div>
            <span className="progress-text">
              {Math.round(activeRenderJob.progress * 100)}%
            </span>
          </div>
          {activeRenderJob.currentScene && (
            <p className="current-scene">
              Procesando: {activeRenderJob.currentScene}
            </p>
          )}
          <button
            className="btn btn-danger"
            onClick={() => handleCancelRender(activeRenderJob.id)}
          >
            Cancelar
          </button>
        </div>
      )}

      <section className="render-history">
        <h2>Historial de Renders</h2>
        {loading ? (
          <div className="loading">Cargando...</div>
        ) : jobs.length === 0 && renderHistory.length === 0 ? (
          <div className="empty-state">
            <p>No hay renders en el historial</p>
          </div>
        ) : (
          <table className="render-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Estado</th>
                <th>Progreso</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {[...renderHistory, ...jobs].map((job) => (
                <tr key={job.id}>
                  <td>#{job.id}</td>
                  <td>
                    <span className={`status status-${job.status}`}>
                      {getStatusLabel(job.status)}
                    </span>
                  </td>
                  <td>
                    <div className="mini-progress">
                      <div
                        className="mini-progress-fill"
                        style={{ width: `${job.progress * 100}%` }}
                      />
                    </div>
                  </td>
                  <td>{new Date(job.createdAt).toLocaleString()}</td>
                  <td>
                    {job.status === "completed" && job.outputPath && (
                      <button className="btn btn-small">Abrir</button>
                    )}
                    {job.status === "failed" && (
                      <button
                        className="btn btn-small"
                        title={job.errorMessage}
                      >
                        Ver Error
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="render-queue">
        <h2>Cola de Render</h2>
        <div className="queue-info">
          <p>
            Los proyectos se renderizan en orden. Puedes agregar mas proyectos a
            la cola desde el Editor.
          </p>
        </div>
      </section>
    </div>
  );
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Pendiente",
    queued: "En Cola",
    processing: "Procesando",
    completed: "Completado",
    failed: "Error",
    cancelled: "Cancelado",
  };
  return labels[status] || status;
}

export default Render;

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { readTextFile } from "@tauri-apps/plugin-fs";

interface Scene {
  id: string;
  duration: string;
  audio?: { text: string; voice: string };
  background?: { color?: string; image?: string };
  character?: { asset: string; position: string; expression: string };
}

function Editor() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get("mode");

  const [yamlContent, setYamlContent] = useState("");
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedScene, setSelectedScene] = useState<string | null>(null);
  const [aiPrompt, setAiPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadProject(parseInt(projectId));
    }
  }, [projectId]);

  async function loadProject(_id: number) {
    // Load project spec from database
    try {
      // For now, initialize with empty spec
      setScenes([]);
    } catch (err) {
      console.error("Failed to load project:", err);
    }
  }

  async function handleImportYaml() {
    try {
      const selected = await open({
        filters: [{ name: "YAML", extensions: ["yaml", "yml"] }],
      });

      if (selected) {
        const content = await readTextFile(selected as unknown as string);
        setYamlContent(content);
        // Parse YAML and extract scenes
        parseYamlContent(content);
      }
    } catch (err) {
      console.error("Failed to import YAML:", err);
      setError("Error al importar archivo YAML");
    }
  }

  function parseYamlContent(content: string) {
    // Simple YAML parsing for scenes
    // In production, use a proper YAML parser
    try {
      const lines = content.split("\n");
      const parsedScenes: Scene[] = [];
      let currentScene: Partial<Scene> | null = null;

      for (const line of lines) {
        if (line.trim().startsWith("- id:")) {
          if (currentScene) {
            parsedScenes.push(currentScene as Scene);
          }
          currentScene = { id: line.split(":")[1].trim() };
        } else if (currentScene && line.includes("duration:")) {
          currentScene.duration = line.split(":")[1].trim().replace(/"/g, "");
        }
      }

      if (currentScene) {
        parsedScenes.push(currentScene as Scene);
      }

      setScenes(parsedScenes);
    } catch {
      setError("Error al parsear YAML");
    }
  }

  async function handleGenerateFromAI() {
    if (!aiPrompt.trim()) return;

    setGenerating(true);
    setError(null);

    try {
      const result = await invoke<string>("generate_from_prompt", {
        prompt: aiPrompt,
      });
      setYamlContent(result);
      parseYamlContent(result);
    } catch (err) {
      console.error("Failed to generate:", err);
      setError("Error al generar con IA");
    } finally {
      setGenerating(false);
    }
  }

  function addScene() {
    const newScene: Scene = {
      id: `scene_${scenes.length + 1}`,
      duration: "5s",
    };
    setScenes([...scenes, newScene]);
    setSelectedScene(newScene.id);
  }

  return (
    <div className="editor-page">
      <header className="page-header">
        <h1>Editor</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleImportYaml}>
            Importar YAML
          </button>
          <button className="btn btn-primary">Guardar</button>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      {mode === "ai" && (
        <div className="ai-prompt-section">
          <h2>Generar con IA</h2>
          <div className="ai-input">
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="Describe el video que quieres crear...&#10;&#10;Ejemplo: Crea un video explicativo de 30 segundos sobre inteligencia artificial, con un presentador animado y fondo azul corporativo."
              rows={4}
            />
            <button
              className="btn btn-primary"
              onClick={handleGenerateFromAI}
              disabled={generating || !aiPrompt.trim()}
            >
              {generating ? "Generando..." : "Generar"}
            </button>
          </div>
        </div>
      )}

      <div className="editor-layout">
        <div className="scenes-panel">
          <div className="panel-header">
            <h3>Escenas</h3>
            <button className="btn btn-icon" onClick={addScene}>
              +
            </button>
          </div>
          <div className="scenes-list">
            {scenes.length === 0 ? (
              <div className="empty-scenes">
                <p>Sin escenas</p>
                <button className="btn btn-secondary" onClick={addScene}>
                  Agregar Escena
                </button>
              </div>
            ) : (
              scenes.map((scene, index) => (
                <div
                  key={scene.id}
                  className={`scene-item ${selectedScene === scene.id ? "selected" : ""}`}
                  onClick={() => setSelectedScene(scene.id)}
                >
                  <span className="scene-number">{index + 1}</span>
                  <div className="scene-info">
                    <span className="scene-id">{scene.id}</span>
                    <span className="scene-duration">{scene.duration}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="preview-panel">
          <h3>Vista Previa</h3>
          <div className="preview-container">
            <div className="preview-placeholder">
              <span>Vista previa no disponible</span>
              <p>Selecciona una escena para ver detalles</p>
            </div>
          </div>
        </div>

        <div className="properties-panel">
          <h3>Propiedades</h3>
          {selectedScene ? (
            <SceneProperties
              scene={scenes.find((s) => s.id === selectedScene)!}
              onChange={(updated) => {
                setScenes(
                  scenes.map((s) => (s.id === updated.id ? updated : s))
                );
              }}
            />
          ) : (
            <div className="no-selection">
              <p>Selecciona una escena para editar</p>
            </div>
          )}
        </div>
      </div>

      <div className="yaml-panel">
        <h3>YAML</h3>
        <textarea
          className="yaml-editor"
          value={yamlContent}
          onChange={(e) => setYamlContent(e.target.value)}
          spellCheck={false}
        />
      </div>
    </div>
  );
}

function SceneProperties({
  scene,
  onChange,
}: {
  scene: Scene;
  onChange: (scene: Scene) => void;
}) {
  return (
    <div className="properties-form">
      <div className="form-group">
        <label>ID</label>
        <input
          type="text"
          value={scene.id}
          onChange={(e) => onChange({ ...scene, id: e.target.value })}
        />
      </div>
      <div className="form-group">
        <label>Duracion</label>
        <input
          type="text"
          value={scene.duration}
          onChange={(e) => onChange({ ...scene, duration: e.target.value })}
          placeholder="5s"
        />
      </div>
      <div className="form-group">
        <label>Texto (Audio)</label>
        <textarea
          value={scene.audio?.text || ""}
          onChange={(e) =>
            onChange({
              ...scene,
              audio: { ...scene.audio, text: e.target.value } as any,
            })
          }
          placeholder="Texto para narrar..."
          rows={3}
        />
      </div>
      <div className="form-group">
        <label>Voz</label>
        <select
          value={scene.audio?.voice || "alloy"}
          onChange={(e) =>
            onChange({
              ...scene,
              audio: { ...scene.audio, voice: e.target.value } as any,
            })
          }
        >
          <option value="alloy">Alloy</option>
          <option value="nova">Nova</option>
          <option value="echo">Echo</option>
          <option value="fable">Fable</option>
          <option value="onyx">Onyx</option>
          <option value="shimmer">Shimmer</option>
        </select>
      </div>
      <div className="form-group">
        <label>Color de Fondo</label>
        <input
          type="color"
          value={scene.background?.color || "#1E3A5F"}
          onChange={(e) =>
            onChange({
              ...scene,
              background: { ...scene.background, color: e.target.value },
            })
          }
        />
      </div>
    </div>
  );
}

export default Editor;

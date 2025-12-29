import { useState } from "react";
import { useStore } from "../hooks/useStore";

function Settings() {
  const { dependencies } = useStore();
  const [settings, setSettings] = useState({
    defaultVoice: "alloy",
    defaultProvider: "openai",
    outputDirectory: "",
    mohoPath: "",
    blenderPath: "",
    ffmpegPath: "",
  });
  const [saved, setSaved] = useState(false);

  function handleSave() {
    // Save settings to local storage or backend
    localStorage.setItem("animatr-settings", JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="settings-page">
      <header className="page-header">
        <h1>Ajustes</h1>
        <button className="btn btn-primary" onClick={handleSave}>
          Guardar
        </button>
      </header>

      {saved && (
        <div className="alert alert-success">Ajustes guardados</div>
      )}

      <section className="settings-section">
        <h2>Estado del Sistema</h2>
        <div className="system-status">
          <StatusItem
            name="Python"
            ok={dependencies.python}
            description="Requerido para el motor de ANIMATR"
          />
          <StatusItem
            name="Moho Pro"
            ok={dependencies.moho}
            description="Para animacion de personajes 2D"
          />
          <StatusItem
            name="Blender"
            ok={dependencies.blender}
            description="Para composicion de escenas 3D"
          />
          <StatusItem
            name="FFmpeg"
            ok={dependencies.ffmpeg}
            description="Para procesamiento de video y audio"
          />
        </div>
      </section>

      <section className="settings-section">
        <h2>Audio y TTS</h2>
        <div className="form-group">
          <label>Proveedor por defecto</label>
          <select
            value={settings.defaultProvider}
            onChange={(e) =>
              setSettings({ ...settings, defaultProvider: e.target.value })
            }
          >
            <option value="openai">OpenAI</option>
            <option value="elevenlabs">ElevenLabs</option>
          </select>
        </div>
        <div className="form-group">
          <label>Voz por defecto</label>
          <select
            value={settings.defaultVoice}
            onChange={(e) =>
              setSettings({ ...settings, defaultVoice: e.target.value })
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
      </section>

      <section className="settings-section">
        <h2>Directorios</h2>
        <div className="form-group">
          <label>Directorio de salida</label>
          <div className="input-with-button">
            <input
              type="text"
              value={settings.outputDirectory}
              onChange={(e) =>
                setSettings({ ...settings, outputDirectory: e.target.value })
              }
              placeholder="~/Videos/ANIMATR"
            />
            <button className="btn btn-secondary">Explorar</button>
          </div>
        </div>
      </section>

      <section className="settings-section">
        <h2>Rutas de Aplicaciones</h2>
        <div className="form-group">
          <label>Moho Pro</label>
          <div className="input-with-button">
            <input
              type="text"
              value={settings.mohoPath}
              onChange={(e) =>
                setSettings({ ...settings, mohoPath: e.target.value })
              }
              placeholder="/Applications/Moho Pro 14.app"
            />
            <button className="btn btn-secondary">Explorar</button>
          </div>
        </div>
        <div className="form-group">
          <label>Blender</label>
          <div className="input-with-button">
            <input
              type="text"
              value={settings.blenderPath}
              onChange={(e) =>
                setSettings({ ...settings, blenderPath: e.target.value })
              }
              placeholder="/Applications/Blender.app"
            />
            <button className="btn btn-secondary">Explorar</button>
          </div>
        </div>
        <div className="form-group">
          <label>FFmpeg</label>
          <div className="input-with-button">
            <input
              type="text"
              value={settings.ffmpegPath}
              onChange={(e) =>
                setSettings({ ...settings, ffmpegPath: e.target.value })
              }
              placeholder="/usr/local/bin/ffmpeg"
            />
            <button className="btn btn-secondary">Explorar</button>
          </div>
        </div>
      </section>

      <section className="settings-section">
        <h2>API Keys</h2>
        <p className="settings-note">
          Las API keys se configuran en el archivo .env del sistema.
          Por seguridad, no se muestran aqui.
        </p>
        <div className="api-status">
          <div className="api-item">
            <span className="api-name">OpenAI</span>
            <span className="api-status-indicator configured">Configurado</span>
          </div>
          <div className="api-item">
            <span className="api-name">ElevenLabs</span>
            <span className="api-status-indicator configured">Configurado</span>
          </div>
          <div className="api-item">
            <span className="api-name">DeepSeek</span>
            <span className="api-status-indicator configured">Configurado</span>
          </div>
        </div>
      </section>
    </div>
  );
}

function StatusItem({
  name,
  ok,
  description,
}: {
  name: string;
  ok: boolean;
  description: string;
}) {
  return (
    <div className={`status-item ${ok ? "ok" : "error"}`}>
      <div className="status-indicator">
        <span className={`dot ${ok ? "ok" : "error"}`}></span>
        <span className="status-name">{name}</span>
      </div>
      <p className="status-description">{description}</p>
      <span className="status-label">{ok ? "OK" : "No encontrado"}</span>
    </div>
  );
}

export default Settings;

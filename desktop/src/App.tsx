import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Projects from "./components/Projects";
import Editor from "./components/Editor";
import Render from "./components/Render";
import Settings from "./components/Settings";
import { useStore } from "./hooks/useStore";

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const { setDependencies } = useStore();

  useEffect(() => {
    // Check system dependencies on startup
    async function checkSystem() {
      try {
        const deps = await invoke<Record<string, boolean>>("check_dependencies");
        setDependencies(deps as { python: boolean; moho: boolean; blender: boolean; ffmpeg: boolean });
      } catch (error) {
        console.error("Failed to check dependencies:", error);
      } finally {
        setIsLoading(false);
      }
    }
    checkSystem();
  }, [setDependencies]);

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loader"></div>
        <p>Iniciando ANIMATR...</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/editor" element={<Editor />} />
            <Route path="/editor/:projectId" element={<Editor />} />
            <Route path="/render" element={<Render />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

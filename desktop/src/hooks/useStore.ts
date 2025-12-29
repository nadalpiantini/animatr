import { create } from "zustand";

interface Project {
  id: number;
  name: string;
  description: string;
  status: string;
  createdAt: string;
}

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

interface Dependencies {
  python: boolean;
  moho: boolean;
  blender: boolean;
  ffmpeg: boolean;
  [key: string]: boolean;
}

interface AppState {
  // Projects
  projects: Project[];
  currentProject: Project | null;
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  addProject: (project: Project) => void;

  // Render
  activeRenderJob: RenderJob | null;
  renderHistory: RenderJob[];
  setActiveRenderJob: (job: RenderJob | null) => void;
  addToRenderHistory: (job: RenderJob) => void;

  // Dependencies
  dependencies: Dependencies;
  setDependencies: (deps: Dependencies) => void;

  // UI
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useStore = create<AppState>((set) => ({
  // Projects
  projects: [],
  currentProject: null,
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project }),
  addProject: (project) =>
    set((state) => ({ projects: [...state.projects, project] })),

  // Render
  activeRenderJob: null,
  renderHistory: [],
  setActiveRenderJob: (job) => set({ activeRenderJob: job }),
  addToRenderHistory: (job) =>
    set((state) => ({ renderHistory: [job, ...state.renderHistory] })),

  // Dependencies
  dependencies: {
    python: false,
    moho: false,
    blender: false,
    ffmpeg: false,
  },
  setDependencies: (deps) => set({ dependencies: deps }),

  // UI
  sidebarCollapsed: false,
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));

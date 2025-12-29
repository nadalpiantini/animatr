//! ANIMATR Desktop Application - Tauri Backend

use serde::{Deserialize, Serialize};
use std::process::Command;
use tauri::Manager;

/// Project information returned from Python backend
#[derive(Debug, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub id: Option<i64>,
    pub name: String,
    pub description: String,
    pub status: String,
    pub created_at: String,
}

/// Render job status
#[derive(Debug, Serialize, Deserialize)]
pub struct RenderStatus {
    pub job_id: i64,
    pub status: String,
    pub progress: f64,
    pub current_scene: Option<String>,
    pub error_message: Option<String>,
}

/// Result of a Python command execution
#[derive(Debug, Serialize, Deserialize)]
pub struct CommandResult {
    pub success: bool,
    pub output: String,
    pub error: Option<String>,
}

/// Execute a Python ANIMATR command
fn run_python_command(args: &[&str]) -> CommandResult {
    let output = Command::new("python")
        .arg("-m")
        .arg("animatr")
        .args(args)
        .output();

    match output {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();

            CommandResult {
                success: output.status.success(),
                output: stdout,
                error: if stderr.is_empty() { None } else { Some(stderr) },
            }
        }
        Err(e) => CommandResult {
            success: false,
            output: String::new(),
            error: Some(e.to_string()),
        },
    }
}

/// List all projects
#[tauri::command]
async fn list_projects() -> Result<Vec<ProjectInfo>, String> {
    let result = run_python_command(&["list", "--json"]);

    if result.success {
        serde_json::from_str(&result.output)
            .map_err(|e| format!("Failed to parse projects: {}", e))
    } else {
        Err(result.error.unwrap_or_else(|| "Unknown error".to_string()))
    }
}

/// Create a new project
#[tauri::command]
async fn create_project(name: String, description: String) -> Result<ProjectInfo, String> {
    let result = run_python_command(&["new", &name, "--description", &description, "--json"]);

    if result.success {
        serde_json::from_str(&result.output)
            .map_err(|e| format!("Failed to parse project: {}", e))
    } else {
        Err(result.error.unwrap_or_else(|| "Failed to create project".to_string()))
    }
}

/// Validate a YAML spec file
#[tauri::command]
async fn validate_spec(path: String) -> Result<bool, String> {
    let result = run_python_command(&["validate", &path]);
    Ok(result.success)
}

/// Start rendering a project
#[tauri::command]
async fn start_render(project_id: i64) -> Result<RenderStatus, String> {
    let id_str = project_id.to_string();
    let result = run_python_command(&["render", "--project-id", &id_str, "--json"]);

    if result.success {
        serde_json::from_str(&result.output)
            .map_err(|e| format!("Failed to parse render status: {}", e))
    } else {
        Err(result.error.unwrap_or_else(|| "Failed to start render".to_string()))
    }
}

/// Get render status
#[tauri::command]
async fn get_render_status(job_id: i64) -> Result<RenderStatus, String> {
    let id_str = job_id.to_string();
    let result = run_python_command(&["status", "--job-id", &id_str, "--json"]);

    if result.success {
        serde_json::from_str(&result.output)
            .map_err(|e| format!("Failed to parse status: {}", e))
    } else {
        Err(result.error.unwrap_or_else(|| "Failed to get status".to_string()))
    }
}

/// Cancel a render job
#[tauri::command]
async fn cancel_render(job_id: i64) -> Result<bool, String> {
    let id_str = job_id.to_string();
    let result = run_python_command(&["cancel", "--job-id", &id_str]);
    Ok(result.success)
}

/// Generate AI script from prompt
#[tauri::command]
async fn generate_from_prompt(prompt: String) -> Result<String, String> {
    let result = run_python_command(&["ai", "generate", "--prompt", &prompt, "--json"]);

    if result.success {
        Ok(result.output)
    } else {
        Err(result.error.unwrap_or_else(|| "Failed to generate".to_string()))
    }
}

/// Check system dependencies
#[tauri::command]
async fn check_dependencies() -> Result<serde_json::Value, String> {
    let result = run_python_command(&["doctor", "--json"]);

    if result.success {
        serde_json::from_str(&result.output)
            .map_err(|e| format!("Failed to parse dependencies: {}", e))
    } else {
        // Return partial info even on failure
        Ok(serde_json::json!({
            "python": true,
            "moho": false,
            "blender": false,
            "ffmpeg": false,
            "error": result.error
        }))
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            list_projects,
            create_project,
            validate_spec,
            start_render,
            get_render_status,
            cancel_render,
            generate_from_prompt,
            check_dependencies,
        ])
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running ANIMATR");
}

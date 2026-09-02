#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;
use chrono::Datelike;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Automatically spawn the FastAPI backend server on startup in development mode (non-blocking)
            #[cfg(debug_assertions)]
            {
                let state = app.state::<BackendProcess>();
                let manifest_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
                let python_path = manifest_dir.join("../backend/.venv/bin/python");
                let project_root = manifest_dir.join("..");
                let backend_root = project_root.join("backend");

                // Ensure backend/logs/YYYY/MM/DD directory exists and prepare uvicorn log redirection (append)
                let now = chrono::Local::now();
                let log_dir = backend_root
                    .join("logs")
                    .join(format!("{:04}", now.year()))
                    .join(format!("{:02}", now.month()))
                    .join(format!("{:02}", now.day()));
                let _ = std::fs::create_dir_all(&log_dir);
                let _ = std::fs::create_dir_all(backend_root.join("data"));
                let log_file_path = log_dir.join("app.log");

                let log_file_result = std::fs::OpenOptions::new()
                    .create(true)
                    .write(true)
                    .append(true)
                    .open(&log_file_path);

                let (stdout_cfg, stderr_cfg) = match log_file_result {
                    Ok(file) => {
                        let stdout_file = file.try_clone().map(std::process::Stdio::from).unwrap_or_else(|_| std::process::Stdio::null());
                        let stderr_file = std::process::Stdio::from(file);
                        (stdout_file, stderr_file)
                    }
                    Err(_) => (std::process::Stdio::null(), std::process::Stdio::null())
                };

                match Command::new(&python_path)
                    .args(&["-m", "uvicorn", "job_search_assistant.api.main:app", "--host", "127.0.0.1", "--port", "8000"])
                    .current_dir(&backend_root)
                    .stdout(stdout_cfg)
                    .stderr(stderr_cfg)
                    .spawn()
                {
                    Ok(child) => {
                        *state.0.lock().unwrap() = Some(child);
                        println!("🚀 FastAPI backend sidecar successfully spawned in background.");
                    }
                    Err(e) => {
                        eprintln!("⚠️ Failed to spawn FastAPI backend at {:?}: {}. Ensure virtual environment exists at .venv.", python_path, e);
                    }
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Terminate the backend sidecar process when the main window closes
                let state = window.state::<BackendProcess>();
                let mut guard = state.0.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    let _ = child.kill();
                    println!("🛑 FastAPI backend sidecar terminated.");
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;
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
                let python_path = manifest_dir.join("../.venv/bin/python");
                let project_root = manifest_dir.join("..");

                match Command::new(&python_path)
                    .args(&["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"])
                    .current_dir(&project_root)
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

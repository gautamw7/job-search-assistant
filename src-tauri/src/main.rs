#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod paths;

use std::process::Child;
use std::sync::Mutex;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let state = app.state::<BackendProcess>();
            let manifest_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
            let project_root = paths::project_root(manifest_dir);

            // Data/log dir: debug -> repo_root/data & logs, release -> app_data_dir
            let data_dir = paths::data_dir(&project_root, app.handle());
            let log_base = paths::log_base(&project_root, app.handle());
            let log_dir = paths::daily_log_dir(&log_base);
            let _ = std::fs::create_dir_all(&log_dir);
            let _ = std::fs::create_dir_all(&data_dir);
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

            // Prefer bundled sidecar binary in release; fallback to python in dev or if binary missing/corrupt
            let mut backend_started = false;
            if let Some(bin) = backend::resolve_sidecar_binary(app.handle()) {
                match backend::spawn_sidecar(&bin, &project_root, &data_dir, stdout_cfg, stderr_cfg) {
                    Ok(child) => {
                        *state.0.lock().unwrap() = Some(child);
                        println!("🚀 Sidecar binary spawned: {:?}", bin);
                        backend_started = true;
                    }
                    Err(e) => {
                        eprintln!("⚠️ Failed to spawn sidecar {:?}: {} — falling back to Python", bin, e);
                    }
                }
            }
            if !backend_started {
                // Reopen log file for Python fallback if sidecar consumed the stdio handles
                let log_file_result = std::fs::OpenOptions::new()
                    .create(true)
                    .write(true)
                    .append(true)
                    .open(&log_file_path);
                let (stdout_cfg2, stderr_cfg2) = match log_file_result {
                    Ok(file) => {
                        let stdout_file = file.try_clone().map(std::process::Stdio::from).unwrap_or_else(|_| std::process::Stdio::null());
                        let stderr_file = std::process::Stdio::from(file);
                        (stdout_file, stderr_file)
                    }
                    Err(_) => (std::process::Stdio::null(), std::process::Stdio::null()),
                };
                let python_path = backend::resolve_python(manifest_dir);
                match backend::spawn_python(&python_path, &project_root, &data_dir, stdout_cfg2, stderr_cfg2) {
                    Ok(child) => {
                        *state.0.lock().unwrap() = Some(child);
                        println!("🚀 FastAPI backend spawned via {:?} (cwd={:?})", python_path, project_root);
                    }
                    Err(e) => eprintln!(
                        "⚠️ Failed to spawn FastAPI backend via {:?} (cwd={:?}): {}. Install uv venv or add python to PATH.",
                        python_path, project_root, e
                    ),
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

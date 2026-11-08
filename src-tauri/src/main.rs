#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod paths;

use std::fs::OpenOptions;
use std::path::Path;
use std::process::{Child, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConfig {
    base_url: String,
    token: String,
}

/// The frontend asks for the per-launch port + token instead of hard-coding them.
#[tauri::command]
fn get_backend_config(config: tauri::State<BackendConfig>) -> BackendConfig {
    config.inner().clone()
}

/// Open a fresh append handle for the backend's stdout/stderr capture file.
fn open_out(path: &Path) -> (Stdio, Stdio) {
    match OpenOptions::new().create(true).append(true).open(path) {
        Ok(file) => {
            let out = file.try_clone().map(Stdio::from).unwrap_or_else(|_| Stdio::null());
            (out, Stdio::from(file))
        }
        Err(_) => (Stdio::null(), Stdio::null()),
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![get_backend_config])
        .setup(|app| {
            let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
            let project_root = paths::project_root(manifest_dir);

            // Debug: repo_root/data & logs. Release: app_data_dir.
            let data_dir = paths::data_dir(&project_root, app.handle());
            let log_base = paths::log_base(&project_root, app.handle());
            let log_dir = paths::daily_log_dir(&log_base);
            let _ = std::fs::create_dir_all(&log_dir);
            let _ = std::fs::create_dir_all(&data_dir);
            // The backend writes app.log itself; this captures raw stdout/stderr
            // (e.g. a crash before logging starts) separately.
            let capture_path = log_dir.join("sidecar.out.log");

            let env = backend::BackendEnv {
                port: backend::pick_free_port(),
                token: backend::generate_token(),
                data_dir,
                log_dir: log_base,
            };
            app.manage(BackendConfig {
                base_url: format!("http://127.0.0.1:{}", env.port),
                token: env.token.clone(),
            });

            let state = app.state::<BackendProcess>();
            let mut started = false;

            // In dev, run the live Python source (a stale frozen binary would hide your edits).
            // In release, prefer the bundled sidecar; fall back to Python if it is missing or dies.
            let prefer_python = cfg!(debug_assertions) && manifest_dir.join("../.venv/bin/python").exists();
            let sidecar = if prefer_python {
                None
            } else {
                backend::resolve_sidecar_binary(app.handle(), &project_root)
            };
            if let Some(bin) = sidecar {
                let (out, err) = open_out(&capture_path);
                match backend::spawn_sidecar(&bin, &project_root, &env, out, err) {
                    Ok(mut child) => {
                        std::thread::sleep(Duration::from_millis(800));
                        match child.try_wait() {
                            Ok(Some(status)) => eprintln!(
                                "⚠️ Sidecar {:?} exited early ({}) — falling back to Python",
                                bin, status
                            ),
                            _ => {
                                *state.0.lock().unwrap() = Some(child);
                                println!("🚀 Sidecar spawned: {:?} on port {}", bin, env.port);
                                started = true;
                            }
                        }
                    }
                    Err(e) => eprintln!(
                        "⚠️ Failed to spawn sidecar {:?}: {} — falling back to Python",
                        bin, e
                    ),
                }
            }

            if !started {
                let python = backend::resolve_python(manifest_dir);
                let (out, err) = open_out(&capture_path);
                match backend::spawn_python(&python, &project_root, &env, out, err) {
                    Ok(child) => {
                        *state.0.lock().unwrap() = Some(child);
                        println!("🚀 FastAPI spawned via {:?} on port {}", python, env.port);
                    }
                    Err(e) => eprintln!(
                        "⚠️ Failed to spawn FastAPI via {:?} (cwd={:?}): {}. Install the uv venv or add python to PATH.",
                        python, project_root, e
                    ),
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            // Exit fires however the app ends (window close, quit, Ctrl+C),
            // unlike a single window's Destroyed event.
            if let tauri::RunEvent::Exit = event {
                let state = app.state::<BackendProcess>();
                let child = state.0.lock().unwrap().take();
                if let Some(child) = child {
                    backend::terminate(child);
                    println!("🛑 Backend terminated.");
                }
            }
        });
}

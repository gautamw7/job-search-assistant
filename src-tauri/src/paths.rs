use std::path::{Path, PathBuf};
use chrono::Datelike;
use tauri::Manager;

pub fn project_root(manifest_dir: &Path) -> PathBuf {
    manifest_dir.join("..")
}

pub fn data_dir(project_root: &Path, app_handle: &tauri::AppHandle) -> PathBuf {
    if cfg!(debug_assertions) {
        project_root.join("data")
    } else {
        let base = app_handle.path().app_data_dir().unwrap_or_else(|_| project_root.to_path_buf());
        base.join("data")
    }
}

pub fn log_base(project_root: &Path, app_handle: &tauri::AppHandle) -> PathBuf {
    if cfg!(debug_assertions) {
        project_root.join("logs")
    } else {
        let base = app_handle.path().app_data_dir().unwrap_or_else(|_| project_root.to_path_buf());
        base.join("logs")
    }
}

pub fn daily_log_dir(log_base: &Path) -> PathBuf {
    let now = chrono::Local::now();
    log_base
        .join(format!("{:04}", now.year()))
        .join(format!("{:02}", now.month()))
        .join(format!("{:02}", now.day()))
}

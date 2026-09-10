use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use tauri::Manager;

pub fn resolve_python(manifest_dir: &Path) -> PathBuf {
    // 1) project-local venv at repo root (uv default after migration)
    let local_root = manifest_dir.join("../.venv/bin/python");
    if local_root.exists() {
        return local_root;
    }
    // 2) legacy backend/.venv for backward compat
    let legacy = manifest_dir.join("../backend/.venv/bin/python");
    if legacy.exists() {
        return legacy;
    }
    // 3) python3 on PATH
    for cand in ["python3", "python"] {
        if let Ok(out) = Command::new("which").arg(cand).output() {
            if out.status.success() {
                let p = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !p.is_empty() {
                    return PathBuf::from(p);
                }
            }
        }
        if Command::new(cand)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            return PathBuf::from(cand);
        }
    }
    PathBuf::from("python3")
}

pub fn resolve_sidecar_binary(app: &tauri::AppHandle) -> Option<PathBuf> {
    if let Ok(resource_dir) = app.path().resource_dir() {
        let candidates = [
            resource_dir.join("binaries/job-search-api-x86_64-unknown-linux-gnu"),
            resource_dir.join("binaries/job-search-api"),
            resource_dir.join("job-search-api"),
        ];
        for c in candidates {
            if c.exists() {
                return Some(c);
            }
        }
    }
    None
}

pub fn spawn_sidecar(
    bin: &Path,
    cwd: &Path,
    data_dir: &Path,
    stdout: std::process::Stdio,
    stderr: std::process::Stdio,
) -> std::io::Result<Child> {
    Command::new(bin)
        .args(["--host", "127.0.0.1", "--port", "8000"])
        .current_dir(cwd)
        .env("JOB_SEARCH_DATA_DIR", data_dir)
        .stdout(stdout)
        .stderr(stderr)
        .spawn()
}

pub fn spawn_python(
    python_path: &Path,
    cwd: &Path,
    data_dir: &Path,
    stdout: std::process::Stdio,
    stderr: std::process::Stdio,
) -> std::io::Result<Child> {
    Command::new(python_path)
        .args(["-m", "uvicorn", "app.app:app", "--host", "127.0.0.1", "--port", "8000"])
        .current_dir(cwd)
        .env("JOB_SEARCH_DATA_DIR", data_dir)
        .stdout(stdout)
        .stderr(stderr)
        .spawn()
}

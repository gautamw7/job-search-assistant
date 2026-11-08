use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hasher};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::Duration;
use tauri::Manager;

/// Everything the backend process needs, decided once per launch.
pub struct BackendEnv {
    pub port: u16,
    pub token: String,
    pub data_dir: PathBuf,
    pub log_dir: PathBuf,
}

/// Ask the OS for a free localhost port so a busy 8000 can never make us talk
/// to some other program.
pub fn pick_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .unwrap_or(8000)
}

/// Per-launch secret the frontend must send as `X-API-Token`. `RandomState` is
/// seeded from OS entropy, so this is unguessable by web pages.
pub fn generate_token() -> String {
    (0..4)
        .map(|_| format!("{:016x}", RandomState::new().build_hasher().finish()))
        .collect()
}

pub fn resolve_python(manifest_dir: &Path) -> PathBuf {
    // 1) project-local venv at repo root (uv default)
    let local_root = manifest_dir.join("../.venv/bin/python");
    if local_root.exists() {
        return local_root;
    }
    // 2) python3 / python on PATH
    for cand in ["python3", "python"] {
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

pub fn resolve_sidecar_binary(app: &tauri::AppHandle, project_root: &Path) -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    // Tauri places externalBin next to the main executable (target triple stripped).
    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            candidates.push(exe_dir.join("job-search-api"));
            candidates.push(exe_dir.join("job-search-api-x86_64-unknown-linux-gnu"));
        }
    }
    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.join("binaries/job-search-api-x86_64-unknown-linux-gnu"));
        candidates.push(resource_dir.join("binaries/job-search-api"));
        candidates.push(resource_dir.join("job-search-api"));
    }
    // Dev: binary built by `make build-sidecar` in the repo.
    candidates.push(project_root.join("binaries/job-search-api-x86_64-unknown-linux-gnu"));

    candidates.into_iter().find(|c| c.is_file())
}

fn apply_env(cmd: &mut Command, env: &BackendEnv, cwd: &Path, out: Stdio, err: Stdio) {
    cmd.current_dir(cwd)
        .env("JOB_SEARCH_DATA_DIR", &env.data_dir)
        .env("JOB_SEARCH_LOG_DIR", &env.log_dir)
        .env("JOB_SEARCH_API_TOKEN", &env.token)
        // The backend exits on its own if this process disappears.
        .env("JOB_SEARCH_PARENT_PID", std::process::id().to_string())
        .stdout(out)
        .stderr(err);
}

pub fn spawn_sidecar(
    bin: &Path,
    cwd: &Path,
    env: &BackendEnv,
    stdout: Stdio,
    stderr: Stdio,
) -> std::io::Result<Child> {
    let mut cmd = Command::new(bin);
    cmd.args(["--host", "127.0.0.1", "--port", &env.port.to_string()]);
    apply_env(&mut cmd, env, cwd, stdout, stderr);
    cmd.spawn()
}

pub fn spawn_python(
    python_path: &Path,
    cwd: &Path,
    env: &BackendEnv,
    stdout: Stdio,
    stderr: Stdio,
) -> std::io::Result<Child> {
    let mut cmd = Command::new(python_path);
    cmd.args([
        "-m",
        "uvicorn",
        "app.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        &env.port.to_string(),
    ]);
    apply_env(&mut cmd, env, cwd, stdout, stderr);
    cmd.spawn()
}

/// Stop the backend politely (SIGTERM lets uvicorn flush), then force it.
pub fn terminate(mut child: Child) {
    #[cfg(unix)]
    {
        let _ = Command::new("kill")
            .args(["-TERM", &child.id().to_string()])
            .status();
        for _ in 0..15 {
            if matches!(child.try_wait(), Ok(Some(_))) {
                return;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

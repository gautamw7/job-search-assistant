import { ToastProvider } from "../context/ToastContext";
import { useBackend } from "../hooks/useBackend";
import { BootScreen } from "./BootScreen";
import { Workspace } from "./Workspace";

function Shell() {
  const backend = useBackend();
  if (backend.state !== "ready") {
    return (
      <BootScreen
        failed={backend.state === "failed"}
        attempt={backend.attempt}
        maxAttempts={backend.maxAttempts}
        onRetry={backend.retry}
      />
    );
  }
  return <Workspace online={backend.online} />;
}

export default function App() {
  return (
    <ToastProvider>
      <Shell />
    </ToastProvider>
  );
}

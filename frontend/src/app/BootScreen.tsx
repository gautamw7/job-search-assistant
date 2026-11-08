import { RefreshCw, ServerCrash } from "lucide-react";
import { Spinner } from "../components/ui";

export function BootScreen({
  failed,
  attempt,
  maxAttempts,
  onRetry,
}: {
  failed: boolean;
  attempt: number;
  maxAttempts: number;
  onRetry: () => void;
}) {
  return (
    <div className="flex h-full w-full items-center justify-center bg-[#080b12] p-6 text-slate-300">
      <div className="flex max-w-sm flex-col items-center gap-4 text-center" role="status" aria-live="polite">
        {failed ? (
          <>
            <ServerCrash className="h-9 w-9 text-rose-400" aria-hidden />
            <p className="text-sm font-semibold text-slate-100">The backend didn't start</p>
            <p className="text-xs text-slate-400">
              The local service that fetches profiles and writes messages isn't responding. Check the latest file in the
              app's <code className="rounded bg-slate-800 px-1">logs</code> folder, then try again.
            </p>
            <button type="button" className="btn btn-primary" onClick={onRetry}>
              <RefreshCw className="h-4 w-4" aria-hidden /> Try again
            </button>
          </>
        ) : (
          <>
            <Spinner className="h-8 w-8 text-indigo-500" />
            <p className="text-sm font-medium">Starting Job Search Assistant…</p>
            <p className="font-mono text-xs text-slate-500">
              Waiting for the backend ({Math.min(attempt, maxAttempts)}/{maxAttempts})
            </p>
          </>
        )}
      </div>
    </div>
  );
}

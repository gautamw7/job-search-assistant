import { useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "../context/ToastContext";

/** Copy to clipboard with a transient "copied" key per button and error feedback. */
export function useCopy() {
  const toast = useToast();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const timer = useRef<number>();

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = useCallback(
    async (text: string, key: string) => {
      try {
        await navigator.clipboard.writeText(text);
        setCopiedKey(key);
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => setCopiedKey(null), 1800);
      } catch {
        toast.error("Couldn't access the clipboard. Select the text and copy it manually.");
      }
    },
    [toast],
  );

  return { copiedKey, copy };
}

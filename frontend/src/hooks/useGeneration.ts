import { useEffect, useRef, useState } from "react";

export function useGeneration() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [genProgressStage, setGenProgressStage] = useState("");
  const cancelRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isGenerating) {
      setElapsedSeconds(0);
      setGenProgressStage("Stage 1/3: Scraping & Enriching Recruiter Profile via BrightData...");
      interval = setInterval(() => {
        setElapsedSeconds((s) => {
          const next = s + 1;
          if (next === 6) setGenProgressStage("Stage 2/3: Analyzing Resume Context & Communication Style...");
          else if (next === 14) setGenProgressStage("Stage 3/3: Drafting Personalized Outreach Message with Gemini AI...");
          return next;
        });
      }, 1000);
    } else {
      setElapsedSeconds(0);
      setGenProgressStage("");
    }
    return () => clearInterval(interval);
  }, [isGenerating]);

  function startGeneration() {
    const controller = new AbortController();
    cancelRef.current = controller;
    setIsGenerating(true);
    return controller;
  }

  function stopGeneration() {
    cancelRef.current?.abort();
  }

  function finishGeneration() {
    cancelRef.current = null;
    setIsGenerating(false);
  }

  return {
    isGenerating,
    elapsedSeconds,
    genProgressStage,
    cancelRef,
    startGeneration,
    stopGeneration,
    finishGeneration,
    setIsGenerating,
  };
}

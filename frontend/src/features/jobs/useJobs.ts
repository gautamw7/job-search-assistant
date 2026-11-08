import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import type { JobListing, JobStatus, JobsMeta, ProfileQuestion, SearchProfile, SearchRun } from "../../types";

export type JobFilters = { status: JobStatus; country: string; startupOnly: boolean; hideGerman: boolean; hideAbove: boolean };

export function useJobs(enabled: boolean) {
  const toast = useToast();
  const [meta, setMeta] = useState<JobsMeta | null>(null);
  const [profile, setProfile] = useState<{ profile: SearchProfile; confirmed: boolean; stale: boolean } | null | undefined>(undefined);
  const [questions, setQuestions] = useState<ProfileQuestion[]>([]);
  const [suggesting, setSuggesting] = useState(false);
  const [run, setRun] = useState<SearchRun | null>(null);
  const [jobs, setJobs] = useState<JobListing[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [filters, setFilters] = useState<JobFilters>({ status: "new", country: "", startupOnly: false, hideGerman: false, hideAbove: true });
  const pollRef = useRef<number>();

  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const data = await api.listJobs({
        status: filters.status,
        country: filters.country || undefined,
        startup_only: filters.startupOnly || undefined,
        hide_german_required: filters.hideGerman || undefined,
        hide_above_level: filters.hideAbove,
      });
      setJobs(data.jobs);
    } catch (e) {
      toast.error(errorMessage(e, "Could not load jobs."));
    } finally {
      setLoadingJobs(false);
    }
  }, [filters, toast]);

  const refreshSetup = useCallback(async () => {
    const [m, p, latest] = await Promise.all([api.jobsMeta(), api.getSearchProfile(), api.latestJobSearch()]);
    setMeta(m);
    setProfile(p);
    setRun(latest);
    if (p?.profile.hide_german_required) setFilters((f) => ({ ...f, hideGerman: true }));
    if (p) setFilters((f) => ({ ...f, hideAbove: p.profile.hide_above_level }));
  }, []);

  useEffect(() => {
    if (enabled) refreshSetup().catch((e) => toast.error(errorMessage(e, "Could not load job search.")));
  }, [enabled, refreshSetup, toast]);

  useEffect(() => {
    if (enabled && profile?.confirmed) loadJobs();
  }, [enabled, profile?.confirmed, loadJobs]);

  const poll = useCallback(
    (id: string) => {
      window.clearInterval(pollRef.current);
      pollRef.current = window.setInterval(async () => {
        try {
          const state = await api.getJobSearch(id);
          setRun(state);
          if (state.status !== "running") {
            window.clearInterval(pollRef.current);
            if (state.status === "done") toast.success("Job search finished.");
            else toast.error(state.error || "Job search failed.");
            loadJobs();
          }
        } catch (e) {
          window.clearInterval(pollRef.current);
          toast.error(errorMessage(e, "Lost track of the search."));
        }
      }, 1500);
    },
    [loadJobs, toast],
  );

  useEffect(() => {
    if (run?.status === "running") poll(run.search_id);
    return () => window.clearInterval(pollRef.current);
  }, [run?.search_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const suggest = useCallback(
    async (ambitions: string) => {
      setSuggesting(true);
      try {
        const r = await api.suggestSearchProfile(ambitions);
        setProfile({ profile: r.profile, confirmed: false, stale: false });
        setQuestions(r.questions);
      } catch (e) {
        toast.error(errorMessage(e, "Could not suggest a profile."));
      } finally {
        setSuggesting(false);
      }
    },
    [toast],
  );

  const saveProfile = useCallback(
    async (p: SearchProfile) => {
      try {
        setProfile(await api.saveSearchProfile(p));
        setQuestions([]);
        toast.success("Search profile saved.");
        return true;
      } catch (e) {
        toast.error(errorMessage(e, "Could not save the profile."));
        return false;
      }
    },
    [toast],
  );

  const search = useCallback(
    async (force = false) => {
      try {
        const r = await api.startJobSearch(force);
        if (r.cached) {
          toast.info("Showing results from a search in the last 24 hours. Use Refresh to search again.");
          setRun(await api.getJobSearch(r.search_id));
          loadJobs();
          return;
        }
        const state = await api.getJobSearch(r.search_id);
        setRun(state);
        poll(r.search_id);
      } catch (e) {
        toast.error(errorMessage(e, "Could not start the search."));
      }
    },
    [loadJobs, poll, toast],
  );

  const setStatus = useCallback(
    async (id: string, status: JobStatus) => {
      try {
        await api.setJobStatus(id, status);
        setJobs((prev) => prev.filter((j) => j.id !== id || status === filters.status));
      } catch (e) {
        toast.error(errorMessage(e, "Could not update the job."));
      }
    },
    [filters.status, toast],
  );

  return { meta, profile, questions, suggesting, run, jobs, loadingJobs, filters, setFilters, suggest, saveProfile, search, setStatus, refreshSetup };
}

import { useEffect, useState } from "react";
import { Sidebar } from "../components/layout/Sidebar";
import { Spinner } from "../components/ui";
import { useCopy } from "../hooks/useCopy";
import { useHistory } from "../hooks/useHistory";
import { useSetup } from "../hooks/useSetup";
import { GeneratorPage } from "../features/generator/GeneratorPage";
import { useGenerator } from "../features/generator/useGenerator";
import { HistoryPage } from "../features/history/HistoryPage";
import { OnboardingWizard } from "../features/onboarding/OnboardingWizard";
import { ResumePage } from "../features/profile/ResumePage";
import { StylePage } from "../features/profile/StylePage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { useKeys } from "../features/settings/useKeys";
import { TrackerPage } from "../features/tracker/TrackerPage";
import { JobsPage } from "../features/jobs/JobsPage";
import { useJobs } from "../features/jobs/useJobs";
import { useTracker } from "../features/tracker/useTracker";
import { useToast } from "../context/ToastContext";
import type { ActiveTab } from "../types";

const TABS: ActiveTab[] = ["generator", "jobs", "tracker", "history", "resume", "style", "config"];

function tabFromHash(): ActiveTab {
  const h = window.location.hash.replace("#", "") as ActiveTab;
  return TABS.includes(h) ? h : "generator";
}

export function Workspace({ online }: { online: boolean }) {
  // The tab lives in the URL hash so reloads and back/forward keep your place.
  const [tab, setTab] = useState<ActiveTab>(tabFromHash);
  useEffect(() => {
    if (window.location.hash !== `#${tab}`) window.history.pushState(null, "", `#${tab}`);
  }, [tab]);
  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    window.addEventListener("popstate", onHash);
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("popstate", onHash);
    };
  }, []);
  const setup = useSetup(true);
  const keys = useKeys(true);
  const history = useHistory(true);
  const tracker = useTracker(true);
  const [jobsVisited, setJobsVisited] = useState(false);
  const jobs = useJobs(jobsVisited);
  const toast = useToast();
  const onHistoryChanged = () => {
    history.refresh();
    tracker.refresh();
  };
  const gen = useGenerator(onHistoryChanged);
  const markSent = async (url: string) => {
    if (await tracker.update(url, { status: "sent" })) {
      toast.success("Marked as sent. It's in the Tracker now.");
      history.refresh();
    }
  };
  const { copiedKey, copy } = useCopy();

  // Re-read keys when the user leaves Settings, so the generator banner stays accurate.
  useEffect(() => {
    if (tab !== "config") keys.refresh();
    if (tab === "tracker") tracker.refresh();
    if (tab === "jobs") {
      // Load lazily on first visit; refresh setup (resume/keys may have changed) on return.
      if (jobsVisited) jobs.refreshSetup().catch(() => undefined);
      setJobsVisited(true);
    }
  }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!setup.loaded) {
    return (
      <div className="flex h-full items-center justify-center bg-[#080b12] text-slate-400">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (setup.error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-[#080b12] p-6 text-center">
        <p className="text-sm text-rose-300">{setup.error}</p>
        <button className="btn btn-primary" onClick={setup.refresh}>
          Try again
        </button>
      </div>
    );
  }

  if (setup.needsResume || setup.needsStyle) {
    return (
      <OnboardingWizard
        needsResume={setup.needsResume}
        copiedKey={copiedKey}
        onCopy={copy}
        onRefresh={setup.refresh}
        onSkipStyle={setup.skipStyle}
      />
    );
  }

  return (
    <div className="flex h-full w-full overflow-hidden bg-[#080b12]">
      <Sidebar activeTab={tab} onChange={setTab} online={online} attention={keys.missing.length ? ["config"] : []}
        badges={{ tracker: tracker.dueCount }}
      />
      <main className="min-w-0 flex-1 overflow-y-auto p-6 lg:p-8">
        {tab === "generator" && (
          <GeneratorPage
            gen={gen}
            history={history.entries}
            cards={history.cards}
            copiedKey={copiedKey}
            onCopy={copy}
            missingKeys={keys.missing}
            onOpenSettings={() => setTab("config")}
            onMarkSent={markSent}
          />
        )}
        {tab === "jobs" && (
          <JobsPage
            jobs={jobs}
            onOpenTab={setTab}
            onOutreach={(job) => {
              gen.addNoteRow(`About the ${job.title} role at ${job.company}: ${job.url}`);
              setTab("generator");
              toast.info("Added a row with the role as a note. Paste the LinkedIn profile of someone at the company.");
            }}
          />
        )}
        {tab === "tracker" && (
          <TrackerPage
            tracker={tracker}
            cards={history.cards}
            copiedKey={copiedKey}
            onCopy={copy}
            onHistoryChanged={onHistoryChanged}
          />
        )}
        {tab === "history" && (
          <HistoryPage
            entries={history.entries}
            cards={history.cards}
            loading={history.loading}
            error={history.error}
            copiedKey={copiedKey}
            onCopy={copy}
            onRefresh={history.refresh}
          />
        )}
        {tab === "resume" && <ResumePage markdown={setup.resume} copiedKey={copiedKey} onCopy={copy} onChanged={setup.refresh} />}
        {tab === "style" && (
          <StylePage saved={setup.style.content} source={setup.style.source} copiedKey={copiedKey} onCopy={copy} onSaved={setup.refresh} />
        )}
        {tab === "config" && <SettingsPage masked={keys.masked} onChanged={keys.refresh} />}
      </main>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import type { Contact, ContactStatus } from "../../types";

export function useTracker(enabled: boolean) {
  const toast = useToast();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [followupDays, setFollowupDays] = useState(4);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.contacts();
      setContacts(data.contacts);
      setFollowupDays(data.followup_after_days);
    } catch (e) {
      toast.error(errorMessage(e, "Could not load the tracker."));
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (enabled) refresh();
  }, [enabled, refresh]);

  const update = useCallback(
    async (url: string, patch: { status?: ContactStatus; notes?: string; followup_sent?: boolean }) => {
      try {
        const tracking = await api.updateContact(url, patch);
        setContacts((prev) => prev.map((c) => (c.linkedin_url === url ? { ...c, ...tracking } : c)));
        // Due dates depend on server-side timing rules; re-read to stay exact.
        refresh();
        return true;
      } catch (e) {
        toast.error(errorMessage(e, "Could not update the contact."));
        return false;
      }
    },
    [refresh, toast],
  );

  const dueCount = contacts.filter((c) => c.followup_due).length;
  return { contacts, followupDays, loading, refresh, update, dueCount };
}

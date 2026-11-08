import { FileText, Pencil, Save, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { api } from "../../api";
import { CopyButton, EmptyState, PageHeader, Spinner } from "../../components/ui";
import { useToast } from "../../context/ToastContext";
import { errorMessage } from "../../lib/http";
import { StructuredResumePanel } from "./StructuredResumePanel";

type Props = {
  markdown: string | null;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  onChanged: () => void;
};

export function ResumePage({ markdown, copiedKey, onCopy, onChanged }: Props) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  const upload = async (file: File) => {
    setUploading(true);
    try {
      await api.uploadResume(file);
      toast.success("Resume replaced.");
      onChanged();
    } catch (e) {
      toast.error(errorMessage(e, "Could not read that PDF."));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.saveResumeMarkdown(draft);
      toast.success("Resume saved.");
      setEditing(false);
      onChanged();
    } catch (e) {
      toast.error(errorMessage(e, "Could not save the resume."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Resume"
        subtitle="Parsed from your PDF. Every message is written from this text, so fix any parsing mistakes here."
        actions={
          <>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
            />
            <button type="button" className="btn btn-secondary" onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? <Spinner /> : <Upload className="h-4 w-4" aria-hidden />} Replace PDF
            </button>
          </>
        }
      />

      <StructuredResumePanel key={markdown ?? "none"} hasResume={!!markdown} />

      {!markdown ? (
        <EmptyState icon={<FileText className="h-6 w-6" />} title="No resume yet" body="Upload a PDF to get started." />
      ) : (
        <section className="card space-y-4 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">{editing ? "Editing resume text" : "Resume text (from your PDF)"}</h3>
            <div className="flex items-center gap-2">
              {editing ? (
                <>
                  <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)} disabled={saving}>
                    <X className="h-4 w-4" aria-hidden /> Cancel
                  </button>
                  <button type="button" className="btn btn-primary" onClick={save} disabled={saving || !draft.trim()}>
                    {saving ? <Spinner /> : <Save className="h-4 w-4" aria-hidden />} Save
                  </button>
                </>
              ) : (
                <>
                  <CopyButton text={markdown} id="resume" copiedKey={copiedKey} onCopy={onCopy} label="Copy" />
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setDraft(markdown);
                      setEditing(true);
                    }}
                  >
                    <Pencil className="h-4 w-4" aria-hidden /> Edit
                  </button>
                </>
              )}
            </div>
          </div>
          {editing ? (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={22}
              aria-label="Resume markdown"
              className="input font-mono leading-relaxed"
            />
          ) : (
            <pre className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-300">
              {markdown}
            </pre>
          )}
        </section>
      )}
    </div>
  );
}

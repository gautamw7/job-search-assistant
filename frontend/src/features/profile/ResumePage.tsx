import { FileText, Pencil, Save, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfVersion, setPdfVersion] = useState(0);

  // Show the uploaded PDF itself, next to the text it was converted into.
  useEffect(() => {
    let url: string | null = null;
    let cancelled = false;
    setPdfUrl(null);
    if (markdown) {
      api
        .resumePdfBlob()
        .then((blob) => {
          if (cancelled) return;
          url = URL.createObjectURL(blob);
          setPdfUrl(url);
        })
        .catch(() => undefined);
    }
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [markdown, pdfVersion]);

  const upload = async (file: File) => {
    setUploading(true);
    try {
      await api.uploadResume(file);
      toast.success("Resume replaced.");
      setPdfVersion((v) => v + 1);
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

      {pdfUrl && (
        <section className="card space-y-3 p-4" aria-label="Uploaded resume PDF">
          <h3 className="text-sm font-semibold text-slate-200">Your uploaded PDF</h3>
          <object data={pdfUrl} type="application/pdf" className="h-[70vh] w-full rounded-xl border border-slate-800 bg-white" aria-label="Resume PDF preview">
            <p className="p-4 text-xs text-slate-600">This window can't preview PDFs here. Use "Replace PDF" to upload a different file.</p>
          </object>
        </section>
      )}

      <StructuredResumePanel key={markdown ?? "none"} hasResume={!!markdown} />

      {!markdown ? (
        <EmptyState
          icon={<FileText className="h-6 w-6" />}
          title="No resume yet"
          body="Upload your PDF. It's converted to text, and you can review the text and the PDF side by side."
          action={
            <button type="button" className="btn btn-primary" onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? <Spinner /> : <Upload className="h-4 w-4" aria-hidden />} Upload resume PDF
            </button>
          }
        />
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

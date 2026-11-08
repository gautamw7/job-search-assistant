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

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Resume"
        subtitle="Your uploaded PDF. Job matching and messages use the reviewed structured copy below."
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

      {!markdown && (
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
      )}
    </div>
  );
}

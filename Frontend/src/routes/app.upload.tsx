import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileAudio, Loader2, X, ArrowRight } from "lucide-react";
import { useAnalysisJob, useActiveJobs, useCreateAnalysis, useCancelJob } from "@/lib/api/hooks";
import { AnalysisPipeline } from "@/components/AnalysisPipeline";
import type { AnalysisJob } from "@/lib/api/types";
import { toast } from "sonner";
import { useMonthlyUsage, usePlan, openUpgradeModal } from "@/lib/billing";
import { AlertCircle } from "lucide-react";
import { useAppState } from "@/lib/store";
import { getEngineBaseUrl } from "@/lib/api/remoteProvider";

// Preflight: ist die lokale Analyse-Engine erreichbar? Verhindert den
// stillen Ausweich auf die schwache Browser-Notauswertung (roter Banner im
// Report) - lieber ehrlich stoppen und zum Engine-Start auffordern.
async function engineReachable(): Promise<boolean> {
  const base = getEngineBaseUrl();
  if (!base) return true; // keine lokale Engine erwartet -> Browser-Pfad ist ok
  try {
    const res = await fetch(`${base}/health`, { signal: AbortSignal.timeout(4000) });
    return res.ok;
  } catch {
    return false;
  }
}

export const Route = createFileRoute("/app/upload")({
  head: () => ({ meta: [{ title: "Upload — MixCoach" }] }),
  component: UploadPage,
});

const ACCEPT = [".mp3", ".wav", ".aiff"];
const MAX_BYTES = 500 * 1024 * 1024;
const ACTIVE_KEY = "mixcoach.activeJobId.v1";

function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [cuePointSec, setCuePointSec] = useState<number>(60);
  const [dragging, setDragging] = useState(false);
  const [jobId, setJobId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : localStorage.getItem(ACTIVE_KEY),
  );
  const inputRef = useRef<HTMLInputElement>(null);
  const inputBRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { data: job } = useAnalysisJob(jobId);
  const activeJobs = useActiveJobs();
  const { create } = useCreateAnalysis();
  const cancelJob = useCancelJob();
  const navigatedRef = useRef(false);
  const { isPro } = usePlan();
  const usage = useMonthlyUsage();
  const [appState] = useAppState();

  useEffect(() => {
    if (!job || navigatedRef.current) return;
    if (job.status === "completed" && job.analysisId) {
      navigatedRef.current = true;
      localStorage.removeItem(ACTIVE_KEY);
      toast.success(job.fromCache ? "Cached analysis restored" : "Analysis ready");
      navigate({ to: "/app/analyses/$id", params: { id: job.analysisId } });
    }
  }, [job, navigate]);

  useEffect(() => {
    if (jobId && job === null && typeof window !== "undefined") {
      const stored = localStorage.getItem(ACTIVE_KEY);
      if (stored === jobId) localStorage.removeItem(ACTIVE_KEY);
      setJobId(null);
    }
  }, [jobId, job]);

  const validate = (f: File): boolean => {
    const ok = ACCEPT.some((e) => f.name.toLowerCase().endsWith(e));
    if (!ok) { toast.error("Unsupported file. Use mp3, wav or aiff."); return false; }
    if (f.size > MAX_BYTES) { toast.error("File too large. Max 500MB."); return false; }
    return true;
  };

  const handleFile = (f: File | null) => { if (f && validate(f)) setFile(f); };
  const handleFileB = (f: File | null) => { if (f && validate(f)) setFileB(f); };

  const start = async () => {
    if (!file) return;
    if (!isPro && usage.capped) {
      openUpgradeModal(`You've used all ${usage.cap} free analyses this month. Upgrade to Pro for unlimited transitions.`);
      return;
    }

    // Preflight: laeuft die Analyse-Engine? Sonst wuerde der Upload still
    // auf die schwache Browser-Notauswertung ausweichen (fast keine
    // Uebergaenge, roter Banner) - das ist fast nie gewollt. Lieber klar
    // stoppen und zum Engine-Start auffordern.
    if (!(await engineReachable())) {
      toast.error(
        "Analyse-Engine nicht erreichbar. Starte MixCoach-Start.bat (beide Fenster offen lassen) und lade dann erneut hoch.",
        { duration: 8000 },
      );
      return;
    }

    // Job-Flow: Upload -> Hintergrund-Analyse im Backend -> Processing-Screen
    // pollt den Fortschritt.
    // (Der alte synchrone Weg blockierte bei 30-min-Sets minutenlang.)
    const id = await create({ file, fileB: fileB ?? undefined, cuePointSec });
    localStorage.setItem(ACTIVE_KEY, id);
    setJobId(id);
    navigate({ to: "/analysis/processing/$jobId", params: { jobId: id } });
  };

  const cancel = async () => {
    if (!jobId) return;
    await cancelJob(jobId);
    localStorage.removeItem(ACTIVE_KEY);
    setJobId(null);
    navigatedRef.current = false;
  };

  // Active analysis view (in-flight job).
  if (job && job.status === "running") {
    return <RunningJobView job={job} onCancel={cancel} />;
  }

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <h1 className="font-display text-3xl font-bold">Upload a transition</h1>
      <p className="text-muted-foreground mt-2">
        Upload one track for a single-track read, or add a second track + cue point for true transition coaching.
      </p>

      {!isPro && (
        <div className={`mt-4 rounded-xl border px-4 py-3 flex items-center justify-between gap-3 text-sm ${
          usage.capped ? "border-primary/50 bg-primary/10" : "border-border bg-card/50"
        }`}>
          <div className="flex items-center gap-2 min-w-0">
            <AlertCircle className={`h-4 w-4 shrink-0 ${usage.capped ? "text-primary" : "text-muted-foreground"}`} />
            <span className="truncate">
              {usage.capped
                ? "You've used all your free analyses this month."
                : <>Free plan · <span className="font-semibold text-foreground">{usage.used}/{usage.cap}</span> analyses used this month</>}
            </span>
          </div>
          <Button size="sm" variant={usage.capped ? "default" : "outline"} onClick={() => openUpgradeModal()}
            className={usage.capped ? "bg-[image:var(--gradient-primary)] border-0 hover:opacity-90" : ""}>
            Upgrade
          </Button>
        </div>
      )}


      {/* Resumable: other in-flight jobs from earlier sessions/tabs. */}
      {activeJobs.length > 0 && (
        <Card className="glass mt-6 border-primary/40">
          <CardContent className="p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="h-9 w-9 rounded-lg bg-[image:var(--gradient-primary)] flex items-center justify-center shrink-0">
                <Loader2 className="h-4 w-4 text-white animate-spin" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-muted-foreground">Analysis in progress</p>
                <p className="font-medium text-sm truncate">{activeJobs[0].fileName}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-display font-bold text-lg w-12 text-right">{activeJobs[0].progress}%</span>
              <Button asChild size="sm" variant="outline">
                <Link to="/analysis/processing/$jobId" params={{ jobId: activeJobs[0].jobId }}>
                  Resume <ArrowRight className="h-3 w-3" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Track A */}
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0] ?? null); }}
        className={`mt-8 block cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all
          ${dragging ? "border-primary bg-primary/5 glow-purple" : "border-border bg-card/40 hover:border-primary/60"}`}
      >
        <input ref={inputRef} type="file" accept={ACCEPT.join(",")} className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)} />
        <p className="eyebrow text-xs text-primary">Track A — outgoing</p>
        <div className="mx-auto mt-3 h-12 w-12 rounded-2xl bg-[image:var(--gradient-primary)] flex items-center justify-center glow-purple">
          {file ? <FileAudio className="h-5 w-5 text-white" /> : <Upload className="h-5 w-5 text-white" />}
        </div>
        {file ? (
          <>
            <p className="mt-3 font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </>
        ) : (
          <>
            <p className="mt-3 font-medium">Drag & drop or click to browse</p>
            <p className="text-xs text-muted-foreground mt-1">MP3, WAV or AIFF — up to 500 MB. Full DJ sets (up to 45 min) are scanned for every transition.</p>
          </>
        )}
      </label>

      {/* Track B (optional) */}
      <label
        className={`mt-4 block cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all
          ${fileB ? "border-accent/60 bg-accent/5" : "border-border/60 bg-card/30 hover:border-accent/60"}`}
      >
        <input ref={inputBRef} type="file" accept={ACCEPT.join(",")} className="hidden"
          onChange={(e) => handleFileB(e.target.files?.[0] ?? null)} />
        <p className="eyebrow text-xs text-accent">Track B — incoming (optional)</p>
        <div className="mx-auto mt-3 h-10 w-10 rounded-xl border border-accent/40 flex items-center justify-center">
          {fileB ? <FileAudio className="h-4 w-4 text-accent" /> : <Upload className="h-4 w-4 text-accent" />}
        </div>
        {fileB ? (
          <p className="mt-2 font-medium text-sm">{fileB.name}</p>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground">Add Track B so I can actually coach the transition — how your tracks sit together, where the bass meets, how the drop lands.</p>
        )}
      </label>

      {/* Cue point — only relevant with two tracks */}
      {fileB && (
        <div className="mt-4 rounded-xl border border-border bg-card/50 p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Cue point in Track A</span>
            <span className="font-mono text-accent">
              {Math.floor(cuePointSec / 60)}:{String(Math.floor(cuePointSec % 60)).padStart(2, "0")}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={240}
            step={1}
            value={cuePointSec}
            onChange={(e) => setCuePointSec(Number(e.target.value))}
            className="mt-3 w-full accent-[var(--primary)]"
          />
          <p className="mt-2 text-xs text-muted-foreground">
            When Track B drops over Track A. Drag to set — the coach analyses a 16-second overlap window starting here.
          </p>
        </div>
      )}

      <div className="mt-6 flex justify-end gap-2">
        {(file || fileB) && (
          <Button variant="ghost" onClick={() => { setFile(null); setFileB(null); }}>Remove</Button>
        )}
        <Button disabled={!file} onClick={start} className="bg-[image:var(--gradient-primary)] border-0 glow-purple hover:opacity-90">
          {fileB ? "Analyse transition" : "Start analysis"}
        </Button>
      </div>
    </div>
  );
}

function RunningJobView({ job, onCancel }: { job: AnalysisJob; onCancel: () => void }) {
  return (
    <div className="max-w-xl mx-auto animate-fade-in">
      <Card className="glass glow-purple">
        <CardContent className="p-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="h-10 w-10 rounded-full bg-[image:var(--gradient-primary)] flex items-center justify-center">
                <Loader2 className="h-5 w-5 text-white animate-spin" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-muted-foreground">Analyzing</p>
                <p className="font-display text-lg font-semibold truncate">{job.fileName}</p>
              </div>
            </div>
            <Button size="icon" variant="ghost" onClick={onCancel} aria-label="Cancel">
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="mt-6">
            <AnalysisPipeline job={job} />
          </div>

          <p className="mt-8 text-xs text-muted-foreground text-center">
            You can leave this page — progress will resume here.{" "}
            <Link to="/app/dashboard" className="underline hover:text-foreground">Back to dashboard</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

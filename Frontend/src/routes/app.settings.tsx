import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useAppState,
  archiveAnalysis,
  unarchiveAnalysis,
  deleteAnalysis,
  clearAllAnalyses,
  clearArchivedAnalyses,
} from "@/lib/store";
import { useJobs } from "@/lib/use-jobs";
import {
  cancelJob,
  removeJob,
  clearCompletedJobs,
  clearAllJobs,
} from "@/lib/analysis-engine";
import { Archive, ArchiveRestore, Trash2, Play, X, Music2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";
import { DeveloperSettings } from "@/components/DeveloperSettings";

const GENRES = ["House", "Tech House", "Melodic House", "Afro House", "Progressive House", "Techno", "Drum & Bass"];
const EQUIPMENT = ["Pioneer DDJ-FLX4", "Pioneer XDJ-XZ", "CDJ-3000", "Denon Prime", "Traktor", "VirtualDJ", "Rekordbox", "Serato"];
const LEVELS = ["Beginner", "Intermediate", "Advanced"] as const;

export const Route = createFileRoute("/app/settings")({
  head: () => ({ meta: [{ title: "Settings — MixCoach" }] }),
  component: Settings,
});

function Settings() {
  const [state, update] = useAppState();
  const p = state.profile;

  const toggle = (list: string[], v: string) =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v];

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-1">Personalize your coaching.</p>
      </div>

      <Card className="glass">
        <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="name">Display name</Label>
            <Input id="name" className="mt-1" value={p.name}
              onChange={(e) => update((s) => ({ ...s, profile: { ...s.profile, name: e.target.value } }))} />
          </div>
          <div>
            <Label>Experience level</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {LEVELS.map((l) => (
                <button key={l} type="button"
                  onClick={() => update((s) => ({ ...s, profile: { ...s.profile, experience: l } }))}
                  className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                    p.experience === l ? "bg-primary text-primary-foreground border-primary" : "border-border hover:border-primary/60"
                  }`}>{l}</button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader><CardTitle>Preferred Genres</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {GENRES.map((g) => {
              const on = p.genres.includes(g);
              return (
                <button key={g} type="button"
                  onClick={() => update((s) => ({ ...s, profile: { ...s.profile, genres: toggle(s.profile.genres, g) } }))}
                  className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                    on ? "bg-accent text-accent-foreground border-accent" : "border-border hover:border-accent/60"
                  }`}>{g}</button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader><CardTitle>Equipment</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {EQUIPMENT.map((eq) => {
              const on = p.equipment.includes(eq);
              return (
                <button key={eq} type="button"
                  onClick={() => update((s) => ({ ...s, profile: { ...s.profile, equipment: toggle(s.profile.equipment, eq) } }))}
                  className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                    on ? "bg-primary/20 text-primary border-primary/50" : "border-border hover:border-primary/40"
                  }`}>{eq}</button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader><CardTitle>Plan</CardTitle></CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <div className="font-semibold">Current plan</div>
            <Badge variant={p.plan === "premium" ? "default" : "secondary"} className="mt-1">{p.plan}</Badge>
          </div>
          <Button onClick={() => { toast.success("Settings saved"); }}>Save changes</Button>
        </CardContent>
      </Card>

      <DataAndCleanup />
      <DeveloperSettings />
    </div>
  );
}

function DataAndCleanup() {
  const [state] = useAppState();
  const jobs = useJobs();
  const [showArchived, setShowArchived] = useState(false);

  const running = jobs.filter((j) => j.status === "running");
  const finished = jobs.filter((j) => j.status !== "running");
  const archived = new Set(state.archivedIds);
  const active = state.analyses.filter((a) => !archived.has(a.id));
  const archivedList = state.analyses.filter((a) => archived.has(a.id));

  return (
    <Card className="glass border-destructive/20">
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div>
          <CardTitle>Data & cleanup</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Manage stored analyses and in-flight jobs. Stored locally on this device.
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-8">
        {/* Resumable / active jobs */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Loader2 className="h-4 w-4 text-accent" />
              Resumable jobs <span className="text-muted-foreground">({running.length})</span>
            </h3>
            {running.length > 0 && (
              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                onClick={() => { running.forEach((j) => cancelJob(j.id)); toast.success("Cancelled all running jobs"); }}>
                Cancel all
              </Button>
            )}
          </div>
          {running.length === 0 ? (
            <EmptyRow text="No analyses currently in progress." />
          ) : (
            <ul className="space-y-2">
              {running.map((j) => (
                <li key={j.id} className="flex items-center justify-between rounded-lg border border-border/60 bg-secondary/30 px-3 py-2">
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{j.fileName}</div>
                    <div className="text-xs text-muted-foreground">{j.overall}% • started {timeAgo(j.startedAt)}</div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button asChild size="sm" variant="ghost">
                      <Link to="/app/upload"><Play className="h-3.5 w-3.5" /> Resume</Link>
                    </Button>
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                      onClick={() => { cancelJob(j.id); toast.success("Job cancelled"); }}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Finished / errored jobs */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">
              Job history <span className="text-muted-foreground">({finished.length})</span>
            </h3>
            <div className="flex gap-2">
              {finished.length > 0 && (
                <Button size="sm" variant="ghost" onClick={() => { clearCompletedJobs(); toast.success("Cleared job history"); }}>
                  Clear history
                </Button>
              )}
              {jobs.length > 0 && (
                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                  onClick={() => { clearAllJobs(); toast.success("Removed all jobs"); }}>
                  Remove all
                </Button>
              )}
            </div>
          </div>
          {finished.length === 0 ? (
            <EmptyRow text="No completed or failed jobs." />
          ) : (
            <ul className="space-y-2">
              {finished.slice(0, 10).map((j) => (
                <li key={j.id} className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2">
                  <div className="min-w-0 flex items-center gap-2">
                    <Badge variant={j.status === "done" ? "secondary" : "destructive"} className="capitalize">{j.status}</Badge>
                    <div className="text-sm truncate">{j.fileName}</div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => removeJob(j.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Analyses */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Music2 className="h-4 w-4 text-accent" />
              Analyses <span className="text-muted-foreground">({active.length} active, {archivedList.length} archived)</span>
            </h3>
            <div className="flex gap-2">
              {archivedList.length > 0 && (
                <Button size="sm" variant="ghost" onClick={() => setShowArchived((v) => !v)}>
                  {showArchived ? "Hide archived" : "Show archived"}
                </Button>
              )}
              {archivedList.length > 0 && (
                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                  onClick={() => {
                    if (!confirm(`Delete ${archivedList.length} archived analyses permanently?`)) return;
                    clearArchivedAnalyses();
                    toast.success("Archived analyses deleted");
                  }}>
                  Empty archive
                </Button>
              )}
              {state.analyses.length > 0 && (
                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
                  onClick={() => {
                    if (!confirm("Delete ALL analyses permanently? This cannot be undone.")) return;
                    clearAllAnalyses();
                    toast.success("All analyses deleted");
                  }}>
                  Delete all
                </Button>
              )}
            </div>
          </div>

          {state.analyses.length === 0 ? (
            <EmptyRow text="You haven't analyzed any transitions yet." />
          ) : (
            <ul className="space-y-2">
              {active.map((a) => (
                <AnalysisRow key={a.id} a={a} archived={false} />
              ))}
              {showArchived && archivedList.map((a) => (
                <AnalysisRow key={a.id} a={a} archived={true} />
              ))}
            </ul>
          )}
        </section>
      </CardContent>
    </Card>
  );
}

function AnalysisRow({ a, archived }: { a: { id: string; fileName: string; createdAt: string; scores: { overall: number | null } }; archived: boolean }) {
  return (
    <li className={`flex items-center justify-between rounded-lg border border-border/60 px-3 py-2 ${archived ? "opacity-60" : ""}`}>
      <div className="min-w-0 flex items-center gap-3">
        <div className="font-display text-lg font-semibold w-8 text-center">{a.scores.overall ?? "—"}</div>
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{a.fileName}</div>
          <div className="text-xs text-muted-foreground">{new Date(a.createdAt).toLocaleDateString()}</div>
        </div>
        {archived && <Badge variant="secondary" className="text-[10px]">Archived</Badge>}
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {archived ? (
          <Button size="sm" variant="ghost" onClick={() => { unarchiveAnalysis(a.id); toast.success("Restored"); }}>
            <ArchiveRestore className="h-3.5 w-3.5" /> Restore
          </Button>
        ) : (
          <Button size="sm" variant="ghost" onClick={() => { archiveAnalysis(a.id); toast.success("Archived"); }}>
            <Archive className="h-3.5 w-3.5" /> Archive
          </Button>
        )}
        <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive"
          onClick={() => {
            if (!confirm(`Delete "${a.fileName}" permanently?`)) return;
            deleteAnalysis(a.id);
            toast.success("Deleted");
          }}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </li>
  );
}

function EmptyRow({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border/60 px-3 py-4 text-center text-xs text-muted-foreground">
      {text}
    </div>
  );
}

function timeAgo(ts: number): string {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

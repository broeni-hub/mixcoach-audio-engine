// Provider selection with automatic fallback.
//
// If VITE_AUDIO_ANALYSIS_API_URL is set, we use the remote Python backend.
// On any failure during job creation we fall back to the in-browser local
// provider so the user still gets a result (marked `fallback: true`).
// Callers can override via setAnalysisProvider in tests.

import type { AnalysisAPI, CreateAnalysisInput, CreateAnalysisResponse } from "./types";
import { localProvider } from "./localProvider";
import { createRemoteProvider } from "./remoteProvider";

let remote = createRemoteProvider();

// Wenn die Engine-URL in den Developer Settings geaendert wird, den
// Remote-Provider neu aufbauen - ohne Seiten-Reload.
if (typeof window !== "undefined") {
  window.addEventListener("mixcoach:engine-status", () => {
    remote = createRemoteProvider();
  });
}

class HybridProvider implements AnalysisAPI {
  name = remote ? "hybrid" : "local";
  private active: AnalysisAPI = remote ?? localProvider;
  // Map remote-issued jobIds → which provider owns them, so polling routes
  // to the right backend after a fallback.
  private routing = new Map<string, AnalysisAPI>();

  private route(jobId: string): AnalysisAPI {
    return this.routing.get(jobId) ?? this.active;
  }

  async createAnalysis(input: CreateAnalysisInput): Promise<CreateAnalysisResponse> {
    if (remote) {
      try {
        const res = await remote.createAnalysis(input);
        this.routing.set(res.jobId, remote);
        return res;
      } catch (err) {
        console.warn("[mixcoach] Remote backend unavailable, falling back to local engine.", err);
      }
    }
    const res = await localProvider.createAnalysis(input);
    this.routing.set(res.jobId, localProvider);
    return res;
  }

  async getJob(jobId: string) {
    const provider = this.route(jobId);
    const job = await provider.getJob(jobId);
    if (job && provider === localProvider) job.fallback = remote ? true : false;
    return job;
  }

  async listJobs() {
    const lists = await Promise.all([
      remote ? remote.listJobs().catch(() => []) : Promise.resolve([]),
      localProvider.listJobs(),
    ]);
    return [...lists[0], ...lists[1]].sort((a, b) => b.startedAt - a.startedAt);
  }

  async cancelJob(jobId: string) {
    await this.route(jobId).cancelJob(jobId);
    this.routing.delete(jobId);
  }

  async retryJob(jobId: string) {
    const provider = this.route(jobId);
    if (provider.retryJob) {
      const res = await provider.retryJob(jobId);
      this.routing.set(res.jobId, provider);
      return res;
    }
    throw new Error("Retry is not supported by the local provider yet.");
  }

  async getAnalysis(id: string) {
    if (remote) {
      try {
        const r = await remote.getAnalysis(id);
        if (r) return r;
      } catch {
        // fall through
      }
    }
    return localProvider.getAnalysis(id);
  }

  async deleteAnalysis(id: string) {
    // Browser-only demo results have no backend file to archive.
    await remote?.deleteAnalysis?.(id);
  }

  subscribe(cb: () => void) {
    const unsubs = [localProvider.subscribe(cb), remote?.subscribe(cb)].filter(Boolean) as Array<() => void>;
    return () => unsubs.forEach((u) => u());
  }
}

let currentProvider: AnalysisAPI = new HybridProvider();

export function getAnalysisProvider(): AnalysisAPI {
  return currentProvider;
}

export function setAnalysisProvider(p: AnalysisAPI) {
  currentProvider = p;
}

export function hasRemoteBackend(): boolean {
  return !!remote;
}

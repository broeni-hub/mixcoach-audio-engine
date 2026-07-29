// React-Query backed hooks over the AnalysisAPI provider.
// Polling every 3s while a job is in-flight; swap to WebSocket later by
// changing only this file.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { getAnalysisProvider } from "./provider";
import type { AnalysisJob, CreateAnalysisInput } from "./types";
import type { AnalysisResult } from "../analysis";

const POLL_MS = 3000;

export function useAnalysisJob(jobId: string | null | undefined) {
  const q = useQuery<AnalysisJob | null>({
    queryKey: ["analysis-job", jobId ?? ""],
    enabled: !!jobId,
    queryFn: () => getAnalysisProvider().getJob(jobId!),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return POLL_MS;
      return data.status === "running" ? POLL_MS : false;
    },
  });
  return q;
}

export function useAnalysisJobs() {
  const qc = useQueryClient();
  const q = useQuery<AnalysisJob[]>({
    queryKey: ["analysis-jobs"],
    queryFn: () => getAnalysisProvider().listJobs(),
    refetchInterval: POLL_MS,
  });
  // Also subscribe to in-provider events so we react instantly to local
  // engine updates between polls.
  useEffect(() => {
    return getAnalysisProvider().subscribe(() => {
      qc.invalidateQueries({ queryKey: ["analysis-jobs"] });
      qc.invalidateQueries({ queryKey: ["analysis-job"] });
    });
  }, [qc]);
  return q;
}

export function useActiveJobs() {
  const { data } = useAnalysisJobs();
  return (data ?? []).filter((j) => j.status === "running");
}

/** Submit a new analysis. Returns a stable callback + the last jobId. */
export function useCreateAnalysis() {
  const [jobId, setJobId] = useState<string | null>(null);
  const create = useCallback(async (input: CreateAnalysisInput) => {
    const { jobId } = await getAnalysisProvider().createAnalysis(input);
    setJobId(jobId);
    return jobId;
  }, []);
  return { create, jobId, setJobId };
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useCallback(
    async (jobId: string) => {
      await getAnalysisProvider().cancelJob(jobId);
      qc.invalidateQueries({ queryKey: ["analysis-jobs"] });
      qc.invalidateQueries({ queryKey: ["analysis-job", jobId] });
    },
    [qc],
  );
}

export function useRetryJob() {
  const qc = useQueryClient();
  return useCallback(async (jobId: string): Promise<string> => {
    const provider = getAnalysisProvider();
    if (!provider.retryJob) throw new Error("Retry not supported");
    const { jobId: nextId } = await provider.retryJob(jobId);
    qc.invalidateQueries({ queryKey: ["analysis-jobs"] });
    qc.invalidateQueries({ queryKey: ["analysis-job"] });
    return nextId;
  }, [qc]);
}

/** Reads the cached AnalysisResult. Today this is the local store; tomorrow
 *  this swaps for a fetch against the provider's GET /analysis/:id. */
export function useAnalysis(id: string | null | undefined): AnalysisResult | null {
  const [a, setA] = useState<AnalysisResult | null>(null);
  useEffect(() => {
    if (!id) { setA(null); return; }
    let cancelled = false;
    void getAnalysisProvider().getAnalysis(id).then((r) => { if (!cancelled) setA(r); });
    const unsub = getAnalysisProvider().subscribe(() => {
      void getAnalysisProvider().getAnalysis(id).then((r) => { if (!cancelled) setA(r); });
    });
    return () => { cancelled = true; unsub(); };
  }, [id]);
  return a;
}

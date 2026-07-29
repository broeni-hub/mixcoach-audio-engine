import { useEffect, useState } from "react";
import {
  bootstrapEngine, subscribe, getJob, listJobs, activeJobs,
  type AnalysisJob,
} from "./analysis-engine";

function useEngineBootstrap() {
  useEffect(() => { bootstrapEngine(); }, []);
}

export function useJob(id: string | null | undefined): AnalysisJob | undefined {
  useEngineBootstrap();
  const [job, setJob] = useState<AnalysisJob | undefined>(() => (id ? getJob(id) : undefined));
  useEffect(() => {
    if (!id) return;
    setJob(getJob(id));
    return subscribe(() => setJob(getJob(id)));
  }, [id]);
  return job;
}

export function useJobs(): AnalysisJob[] {
  useEngineBootstrap();
  const [jobs, setJobs] = useState<AnalysisJob[]>(() => listJobs());
  useEffect(() => {
    setJobs(listJobs());
    return subscribe(() => setJobs(listJobs()));
  }, []);
  return jobs;
}

export function useActiveJobs(): AnalysisJob[] {
  useEngineBootstrap();
  const [jobs, setJobs] = useState<AnalysisJob[]>(() => activeJobs());
  useEffect(() => {
    setJobs(activeJobs());
    return subscribe(() => setJobs(activeJobs()));
  }, []);
  return jobs;
}

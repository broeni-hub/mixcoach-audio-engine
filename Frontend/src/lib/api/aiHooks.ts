// Future AI hooks — interfaces only. A Python backend will implement these.
// Frontend wires UI to these signatures so plug-in is zero-redesign.

import type { AnalysisResult } from "../analysis";

function notImplemented(name: string): never {
  throw new Error(`[ai-hooks] ${name} is not implemented in localProvider — plug a Python backend.`);
}

export interface StemSeparator {
  separate(file: File): Promise<{ vocals: Blob; drums: Blob; bass: Blob; other: Blob }>;
}
export interface PhraseDetector {
  detect(file: File): Promise<{ barStarts: number[]; phraseStarts: number[] }>;
}
export interface HarmonicMixer {
  recommend(currentKey: string): Promise<string[]>;
}
export interface VocalDetector {
  detect(file: File): Promise<{ segments: { start: number; end: number }[] }>;
}
export interface EnergyModel {
  predict(file: File): Promise<{ curve: { t: number; value: number }[] }>;
}
export interface EQAnalyzer {
  analyze(file: File): Promise<{ bass: number; mid: number; high: number }>;
}
export interface CrowdEnergyPredictor {
  predict(analysis: AnalysisResult): Promise<{ expectedReaction: number; confidence: number }>;
}

export const aiHooks: {
  stems: StemSeparator;
  phrases: PhraseDetector;
  harmonic: HarmonicMixer;
  vocals: VocalDetector;
  energy: EnergyModel;
  eq: EQAnalyzer;
  crowd: CrowdEnergyPredictor;
} = {
  stems: { separate: () => notImplemented("StemSeparator.separate") },
  phrases: { detect: () => notImplemented("PhraseDetector.detect") },
  harmonic: { recommend: () => notImplemented("HarmonicMixer.recommend") },
  vocals: { detect: () => notImplemented("VocalDetector.detect") },
  energy: { predict: () => notImplemented("EnergyModel.predict") },
  eq: { analyze: () => notImplemented("EQAnalyzer.analyze") },
  crowd: { predict: () => notImplemented("CrowdEnergyPredictor.predict") },
};

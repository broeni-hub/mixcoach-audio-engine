// Validates the anti-hallucination guard rails in the coach prompt.
//
// The prompt is the only thing standing between real measurements and
// fabricated coaching text. These tests pin the strict grounding rules
// so they can't be silently removed.

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const promptModule = readFileSync(
  resolve(__dirname, "../coach-feedback.functions.ts"),
  "utf8",
);

describe("coach-feedback prompt grounding guard", () => {
  it("forbids inventing numbers", () => {
    expect(promptModule).toMatch(/NEVER invent numbers/i);
  });

  it("forbids fabricated history / improvement claims (only one snapshot is visible)", () => {
    expect(promptModule).toMatch(/improved|got worse|changed/i);
    expect(promptModule).toMatch(/ONE snapshot|one snapshot/);
  });

  it("forbids speculation about crowd / mood / genre", () => {
    expect(promptModule).toMatch(/crowd|mood|genre/i);
  });

  it("requires hedging when BPM or key confidence is low", () => {
    expect(promptModule).toMatch(/BPM confidence/);
    expect(promptModule).toMatch(/key confidence/);
    expect(promptModule).toMatch(/hedge|may be wrong/i);
  });

  it("instructs the model to omit unknown values rather than inventing them", () => {
    expect(promptModule).toMatch(/If a value isn't in the data, do not mention it/);
  });

  // --- Die belegten Groessen (seit 15.08.2026) ----------------------------
  // Bis dahin kannte der Prompt ausgerechnet die zwei Groessen nicht, fuer
  // die ein Zusammenhang mit Sebastians Urteil belegt ist - er sprach
  // stattdessen ueber bass_clash_score, fuer den nie einer erhoben wurde.

  it("kennt den Pegelsprung und nennt ihn das staerkste Signal", () => {
    expect(promptModule).toMatch(/loudness_jump_db/);
    expect(promptModule).toMatch(/STRONGEST SIGNAL/);
    expect(promptModule).toMatch(/0 dB is a seamless match/);
  });

  it("kennt beat_alignment und daempft es zugleich", () => {
    expect(promptModule).toMatch(/beat_alignment_score/);
    // Es korreliert (+0,325), hat aber kaum Spannweite - der Prompt sagt das,
    // damit das Modell nicht die ganze Antwort darauf baut.
    expect(promptModule).toMatch(/varies little/);
  });

  it("erfindet keine Pflichtfelder zurueck", () => {
    // Beide sind nullable. Faellt das weg, muesste jeder Aufrufer eine Zahl
    // liefern - und genau daraus sind am 13.08. die erfundenen Messwerte
    // entstanden.
    const schema = promptModule.slice(
      promptModule.indexOf("const TransitionZ"),
      promptModule.indexOf("const InputZ"),
    );
    expect(schema).toMatch(/loudness_jump_db: z\.number\(\)\.nullable\(\)/);
    expect(schema).toMatch(/beat_alignment_score: z\.number\(\)\.nullable\(\)/);
  });

  it("retry prompt also forbids invented numbers", () => {
    // The reduced retry prompt must keep the same grounding contract.
    const retrySection = promptModule.slice(promptModule.indexOf("buildRetryPrompt"));
    expect(retrySection).toMatch(/Do NOT invent numbers/);
  });
});

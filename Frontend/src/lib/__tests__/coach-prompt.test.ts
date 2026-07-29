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

  it("retry prompt also forbids invented numbers", () => {
    // The reduced retry prompt must keep the same grounding contract.
    const retrySection = promptModule.slice(promptModule.indexOf("buildRetryPrompt"));
    expect(retrySection).toMatch(/Do NOT invent numbers/);
  });
});

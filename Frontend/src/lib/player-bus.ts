// Winziger Vermittler zwischen Waveform-Player und Feedback-Buttons:
// Der Player meldet laufend seine Position; die "Startet woanders"-Buttons
// lesen sie beim Klick aus. Kein React-State noetig - reiner Modulwert.

let currentSec = 0;
let hasAudio = false;

export function reportPlayerPosition(sec: number) {
  currentSec = sec;
  hasAudio = true;
}

export function getPlayerPosition(): { sec: number; hasAudio: boolean } {
  return { sec: currentSec, hasAudio };
}

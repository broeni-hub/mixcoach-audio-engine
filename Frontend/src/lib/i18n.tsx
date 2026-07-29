// Leichtgewichtige Sprachweiche DE/EN fuer das gesamte Frontend.
// - Sprache liegt in localStorage ("mixcoach.lang"), Default: Browser-Sprache
// - useLang() macht Komponenten reaktiv auf den Umschalter
// - Texte leben als kleine {de, en}-Woerterbuecher direkt bei den Komponenten

import { useSyncExternalStore } from "react";

export type Lang = "de" | "en";

const STORAGE_KEY = "mixcoach.lang";
const listeners = new Set<() => void>();

function detect(): Lang {
  if (typeof window === "undefined") return "de";
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "de" || saved === "en") return saved;
  } catch { /* private mode etc. */ }
  return navigator.language?.toLowerCase().startsWith("de") ? "de" : "en";
}

let current: Lang = detect();

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang) {
  current = lang;
  try {
    window.localStorage.setItem(STORAGE_KEY, lang);
  } catch { /* egal */ }
  listeners.forEach((fn) => fn());
}

export function useLang(): Lang {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => current,
    () => "de" as Lang,
  );
}

/** Kleiner Helfer: waehlt aus einem {de, en}-Objekt die aktive Sprache. */
export function pick<T>(lang: Lang, texts: { de: T; en: T }): T {
  return texts[lang];
}

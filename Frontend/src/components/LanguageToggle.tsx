// DE|EN-Umschalter (Sidebar). Wirkt sofort auf alle Komponenten mit useLang().

import { setLang, useLang } from "@/lib/i18n";

export function LanguageToggle({ collapsed }: { collapsed?: boolean }) {
  const lang = useLang();
  if (collapsed) return null;
  return (
    <div className="flex items-center gap-1 px-2 py-1">
      {(["de", "en"] as const).map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          className={`rounded px-2 py-0.5 text-[11px] font-semibold uppercase transition-colors ${
            lang === l
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

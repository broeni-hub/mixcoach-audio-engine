// Zeigt den Fortschritt bis zum naechsten automatischen Modell-Training.
// Motiviert die Label-Arbeit: jedes bestaetigte/korrigierte Set bringt den
// DJ sichtbar naeher an eine bessere Erkennung. Rendert nichts, wenn das
// Backend nicht erreichbar ist (ehrlich: keine erfundenen Zahlen).

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain, CheckCircle2 } from "lucide-react";
import { fetchCalibrationStatus, type CalibrationStatus } from "@/lib/calibration";

export function CalibrationProgress() {
  const [status, setStatus] = useState<CalibrationStatus | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    fetchCalibrationStatus().then((s) => { setStatus(s); setLoaded(true); });
  }, []);

  if (!loaded || !status || !status.modelExists) return null;

  const pct = Math.min(100, Math.round((status.newSets / Math.max(1, status.threshold)) * 100));
  const am = status.activeModel;

  return (
    <Card className="border-primary/30">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold">Erkennung wird mit deinem Feedback besser</span>
          {status.ready && (
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">Training bereit</Badge>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>{status.newSets} von {status.threshold} neuen Sets bis zum nächsten Auto-Training</span>
            <span>{status.totalLabeled} gelabelt gesamt</span>
          </div>
          <div className="h-2 rounded-full bg-secondary overflow-hidden">
            <div className="h-full bg-[image:var(--gradient-primary)]" style={{ width: `${pct}%` }} />
          </div>
        </div>

        {status.ready ? (
          <p className="text-xs text-emerald-400/90 flex items-start gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            Genug neues Feedback gesammelt — starte <span className="font-mono">MixCoach-Retrain.bat</span>, um ein besseres Modell zu trainieren (nur aktiv, wenn es wirklich besser ist).
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Jedes bestätigte oder korrigierte Set trainiert die Erkennung weiter. Bei {status.threshold} neuen Sets lohnt sich das nächste Training.
          </p>
        )}

        {am.f1 != null && (
          <p className="text-[11px] text-muted-foreground/80">
            Aktuelles Modell: Treffer {am.recall != null ? Math.round(am.recall * 100) : "—"}% ·
            Genauigkeit {am.precision != null ? Math.round(am.precision * 100) : "—"}%
          </p>
        )}
      </CardContent>
    </Card>
  );
}

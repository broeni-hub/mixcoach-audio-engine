"""MixCoach – zentrale, verankerte Datenpfade.

Bisher lagen zusammengehoerige Daten an drei Orten:
  - Ergebnisse: %LOCALAPPDATA%/MixCoach/analysis_results (job_manager)
    oder MIXCOACH_DATA_DIR/analysis_results (wenn Variable gesetzt)
  - Ground Truth: ./ground_truth relativ zum Server-Startverzeichnis
    (feedback_store)
Dadurch sind Ergebnisse "verschwunden", sobald sich Startverzeichnis
oder Umgebungsvariable geaendert haben.

Ab jetzt gilt EIN Datenstamm fuer alles:
  1. MIXCOACH_DATA_DIR, falls gesetzt (bewusster Override fuer
     Deployment oder um grosse Audiodateien auf eine andere Platte
     zu legen)
  2. sonst der Projektordner (diese Datei liegt in app/, der Stamm
     ist eine Ebene darueber) - unabhaengig davon, von wo der Server
     gestartet wird.

Hinweis: Der fruehere AppData-Standard existierte, weil das Projekt in
OneDrive lag und grosse Audio-Kopien den Sync lahmgelegt haben. Das
Projekt liegt inzwischen ausserhalb von OneDrive; sollte es jemals
zurueck in einen Sync-Ordner ziehen, einfach MIXCOACH_DATA_DIR auf
einen Ordner ausserhalb setzen.
"""

import os
from pathlib import Path

# Diese Datei liegt in app/ -> parents[1] ist der Projektstamm.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = Path(os.environ.get("MIXCOACH_DATA_DIR", PROJECT_ROOT))

RESULTS_DIR = DATA_ROOT / "analysis_results"
GROUND_TRUTH_DIR = DATA_ROOT / "ground_truth"

# Ordner beim Import sicherstellen - kein Aufrufer muss sich darum kuemmern.
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

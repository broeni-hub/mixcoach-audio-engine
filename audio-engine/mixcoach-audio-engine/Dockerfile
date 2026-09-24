# MixCoach Audio-Engine als Container.
#
# WAS HIER BELEGT IST UND WAS NICHT (24.09.2026)
# ----------------------------------------------
# BELEGT: die Paketliste. Eine frische Umgebung nur aus
# requirements-server.txt startet die Engine, liefert /health, /analysis und
# einen vollstaendigen Report, und traegt mit requirements-dev.txt alle 488
# Tests. Nachgemessen, nicht geschaetzt.
#
# NICHT BELEGT: dieses Dockerfile selbst. Auf dem Mac, auf dem es entstanden
# ist, gibt es kein Docker - der Build ist nie gelaufen. Die Python-Schicht
# ist geprueft, die Debian-Schicht (apt, Basis-Image) nicht. Wer es zum
# ersten Mal baut, rechnet mit einer Runde Nacharbeit und traegt sie hier ein.
#
# WARUM SO KLEIN
# --------------
# Der Quelltext ist winzig (app 8,7 MB, tools 1,7 MB). Die 8,6 GB im Ordner
# sind synthetische Datensaetze, Archive und Beispiel-Audio - alles in
# .dockerignore. Zwei schwere Abhaengigkeiten fallen weg:
#   scikit-learn     nur fuers Nachtrainieren, Inferenz laeuft in numpy
#   ffmpeg           nicht noetig, soundfile bringt libsndfile 1.2.2 mit,
#                    die MP3 kann (nachgeprueft)
# torch und demucs bleiben drin - siehe MIT_STEMS weiter unten.
#
# ARCHITEKTUR: dieser Mac ist arm64 (Apple M5), die meisten Hoster laufen
# amd64. Ein hier gebautes Image passt nicht ohne Weiteres dorthin. Entweder
# beim Hoster bauen lassen (fly deploy, Render, Cloud Run bauen selbst) oder
# lokal mit  --platform linux/amd64  - dann emuliert, also langsam.
#
# DIE DATEN GEHOEREN NICHT INS IMAGE.
# daten/analysis_results ist 15 GB, daten/library 1,7 GB. Beides kommt als
# Volume unter /daten. Ohne MIXCOACH_DATA_DIR faellt app/paths.py auf den
# Engine-Ordner zurueck und die App sucht Library, Ergebnisse und Ground
# Truth am falschen Ort - genau so sind die Ground-Truth-Staemme einmal
# auseinandergelaufen.

FROM python:3.12-slim AS basis

# libgomp1: OpenMP-Laufzeit, die numba/llvmlite (ueber librosa) und scipy
# erwarten. Sonst nichts - kein ffmpeg, kein libsndfile-Paket.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /engine

# Abhaengigkeiten vor dem Quelltext: so bleibt die teure Schicht im Cache,
# wenn sich nur Code aendert.
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# STEM-TRENNUNG: Werkzeug an Bord, Schalter aus (Entscheidung 24.09.2026).
#
# torch, demucs und die htdemucs-Gewichte liegen im Image - aber
# MIXCOACH_ENABLE_STEM_SCORING steht auf 0 (weiter unten). Umlegen geht
# damit zur Laufzeit, ohne neues Image:
#
#     docker run -e MIXCOACH_ENABLE_STEM_SCORING=1 ...
#
# WARUM AUS. Am 24.09.2026 an einem echten 44,5-Minuten-Set nachgemessen
# (Apple M5, Demucs auf CPU - nicht MPS, nachgeprueft):
#
#     ohne Stems    64,3 s
#     mit Stems    130,5 s     10 von 10 Uebergaengen mit Stem-Werten
#     Anteil Demucs           51 % der Rechenzeit
#
# Und der einzige Abnehmer dieser Werte ist composite_quality_score, den das
# Frontend nirgends ausliest. Am selben Tag nachgezaehlt unter Frontend/src:
# harmonic_clash 0 Treffer, vocal_overlap 0, exit_quality 0,
# composite_quality_score 2 - beide in Kommentaren. Derselbe Befund steht
# seit dem 30.07.2026 in app/audio/pipeline/pipeline.py, der den Schalter
# damals ausgeschaltet hat.
#
# Rechenzeit ist der Kostentreiber beim Hosting, nicht der Speicher: auf
# einer dreimal langsameren Cloud-CPU sind das rund 3 min je Set statt 6,5.
#
# Wer das Image ganz ohne die 530 MB will:  --build-arg MIT_STEMS=0
ARG MIT_STEMS=1

# torch aus dem CPU-Index. Das Standard-Rad zieht auf linux/amd64 die
# CUDA-Bibliotheken mit - rund 2,5 GB fuer eine GPU, die kein Container hier
# hat. Die CPU-Fassung ist ein Bruchteil davon.
RUN if [ "$MIT_STEMS" = "1" ]; then \
      pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        torch==2.13.0 demucs==4.1.0 ; \
    fi

# Die Modell-Gewichte JETZT holen, nicht beim ersten Nutzer.
#
# app/audio/scoring/stems.py sagt es selbst: "Der ALLERERSTE Aufruf laedt
# zusaetzlich die Modell-Gewichte aus dem Internet (einmalig, mehrere hundert
# MB)". In einem Container heisst "einmalig pro Prozess" = bei JEDEM
# Neustart, solange nichts zwischengespeichert ist. Ein DJ wuerde beim ersten
# Set minutenlang warten, und ohne Netz schlaegt die Trennung still fehl.
#
# Deshalb liegen die Gewichte im Image.
#
# ACHTUNG, HIER STAND ZUERST DAS FALSCHE: TORCH_HOME. Demucs 4.1 holt
# htdemucs nicht aus dem torch-Hub, sondern vom HuggingFace Hub - am
# 24.09.2026 nachgesehen, die Dateien liegen unter
# ~/.cache/huggingface/hub/models--adefossez--HTDemucs. Mit TORCH_HOME haette
# der Build die Gewichte zwar geladen, aber an eine Stelle, die zur Laufzeit
# niemand liest - und jeder Container haette sie doch wieder heruntergeladen.
# Beide Variablen stehen jetzt da; die wirksame ist HF_HOME.
ENV TORCH_HOME=/engine/.torch \
    HF_HOME=/engine/.cache/huggingface
RUN if [ "$MIT_STEMS" = "1" ]; then \
      python -c "from demucs.api import Separator; Separator(model='htdemucs', progress=False)" ; \
    fi

COPY app  ./app
COPY tools ./tools

# Nicht als root. Das Volume muss dieser UID gehoeren.
RUN useradd --create-home --uid 10001 mixcoach && chown -R mixcoach:mixcoach /engine
USER mixcoach

# PFLICHT, kein Standardwert im Code - siehe Kopf.
ENV MIXCOACH_DATA_DIR=/daten
VOLUME ["/daten"]

# Stem-Scoring aus - siehe die lange Begruendung bei MIT_STEMS. Das Werkzeug
# ist da, nur der Schalter steht auf 0. Zur Laufzeit umlegbar.
ENV MIXCOACH_ENABLE_STEM_SCORING=0

# Vorgabe ist AUS und nur fuer 127.0.0.1 gedacht. Wer den Container ins Netz
# stellt, setzt MIXCOACH_AUTH=an und SUPABASE_URL - sonst steht die Engine
# offen. app/auth.py nennt die Betriebsart beim Start und unter /health.
ENV MIXCOACH_AUTH=aus

EXPOSE 8000

# Kein curl im slim-Image - Python fragt selbst.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

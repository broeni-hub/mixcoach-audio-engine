#!/bin/bash
# ============================================================
#  MixCoach-Retrain-Jetzt: trainiert das Modell SOFORT neu,
#  ohne auf "genug neue Sets" zu warten.
#
#  Wie MixCoach-Retrain.command, aber mit --force: laeuft auch
#  bei wenigen neuen Labels. Praktisch direkt nach dem Labeln -
#  und der Weg, um den am 10.08.2026 erweiterten Betriebspunkt
#  (gap bis 150 s statt 90 s) wirksam werden zu lassen.
#
#  Trainiert wie ueberall NUR mit echten Sets. Neues Modell wird
#  NUR aktiviert, wenn es das Gate besteht; das alte wird als
#  .backup gesichert.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/MixCoach-Retrain.command" --force

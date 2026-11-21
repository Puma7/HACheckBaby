# CheckBaby

Lokales, smartes Babyphone für Home Assistant auf Basis von Frigate, installiert über HACS.

[English version](README.md)

**Status: frühe Entwicklung.** Die Integration lässt sich installieren und für ein Kind einrichten, überwacht aber noch nichts. Erkennung, Alarme und Ausfallüberwachung kommen mit Version 0.1 (Phase 1 des Plans).

**CheckBaby ist kein Medizinprodukt.** Es kann den plötzlichen Kindstod nicht verhindern und kann ohne Vorwarnung ausfallen. Es unterstützt die Aufsicht durch die Eltern und die Regeln für sicheren Babyschlaf, ersetzt aber beides nicht.

## Plan

Der vollständige Plan steht in [docs/MASTERPLAN.md](docs/MASTERPLAN.md): Architektur, Alarmstufen, Hardware, Funktionsliste und Zeitplan.

## Installation (zum Testen)

1. In HACS `https://github.com/Puma7/HACheckBaby` als benutzerdefiniertes Repository vom Typ „Integration" hinzufügen.
2. „CheckBaby" installieren und Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → CheckBaby.

Benötigt Home Assistant 2026.2 oder neuer.

## Entwicklung

Siehe [AGENTS.md](AGENTS.md) und die [Checkliste für Phase 0](docs/development/phase-0-checkliste.md).

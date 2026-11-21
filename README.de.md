# CheckBaby

Ein lokales Babyphone für Home Assistant auf Basis von Frigate, installiert über HACS. Es macht aus den Signalen von Frigate für Weinen, Geräuschpegel und Bewegung, aus optionalen Sensoren und einer optionalen KI-Bewertung einen Zustand des Kindes und Alarme in drei Stufen.

[English version](README.md) · [Dokumentation](docs/de/README.md) · [Documentation](docs/en/README.md)

**CheckBaby ist kein Medizinprodukt.** Es kann den plötzlichen Kindstod nicht verhindern und kann ohne Vorwarnung ausfallen. Es unterstützt deine Aufsicht und die Regeln für sicheren Babyschlaf, ersetzt aber beides nicht. Behalte ein einfaches Babyphone als Rückfallebene.

## Stand und Grenzen

Version 0.1.0 ist noch nicht veröffentlicht. Lies das, bevor du installierst.

- Die Integration ist durch automatische Tests abgedeckt, die gegen Home Assistant 2026.2 und 2026.10 laufen.
- **Sie lief noch nie an einem echten Frigate, einer echten Kamera, einem Handy oder einem Radarsensor.** Die MQTT-Themen, das Format der Push-Nachrichten und der KI-Aufruf folgen der Dokumentation von Frigate, der Home-Assistant-App und Home Assistant. Ob sie zu deinem System passen, zeigt der erste Abend.
- Die Vital-Engine (`engine/`) wurde nur mit künstlichen Signalen getestet und hat noch nie eine echte Kamera oder ein echtes Kind gesehen.
- Alle Hardware-Beispiele (Frigate-Konfiguration, ESPHome für Radar und Summer, Dashboards, Blueprints) sind an echter Hardware ungetestet.
- Der Atembewegungs-Hinweis ist an Säuglingen nicht validiert und standardmäßig ausgeschaltet. Er ist ein Hinweis, keine medizinische Messung.

## Was heute funktioniert

„Funktioniert" heißt: umgesetzt und durch die automatischen Tests abgedeckt.

- **Einrichtung in der Oberfläche:** Kind, Schlafplätze mit Kamera und Sensoren, wer benachrichtigt wird, Hinweis zur Zweckbestimmung. Mehrere Schlafplätze je Kind, mehrere Kinder.
- **Quellen:** Frigate über MQTT (Weinen, Schrei, Geräuschpegel, Bewegung, Person, Katze oder Hund in der Bett-Zone, Verfügbarkeit) oder einfache Entitäten für Weinen, Bewegung und Pegel. Optional Türkontakt, Präsenz im Bett, Raumklima, Rauch/CO, Internetverbindung.
- **Zustand des Kindes:** schläft, unruhig, wach, weint, betreut, nicht im Bett, unbekannt. Wechsel folgen aus Dauern, nicht aus Einzelereignissen.
- **Alarme in drei Stufen:** Hinweis, Warnung, kritisch. Push-Nachrichten mit Kamerabild und den Knöpfen „Gesehen", „5 min Ruhe" und „Live"; kritische Alarme so gesendet, dass sie trotz „Nicht stören" ertönen, wiederholt alle 30 Sekunden; ein lokaler Alarm (Sirene, Licht) nach einer Minute; „Hat Dienst" und ein Babysitter-Modus.
- **Ausfallüberwachung:** Jede Quelle wird überwacht, und ein Ausfall wird gemeldet, statt „schläft" anzuzeigen. Meldungen beim Herunterfahren und nach einer Unterbrechung; Herzschlag für einen externen Dead-Man-Summer.
- **Gelernter Grundpegel**, damit weißes Rauschen nicht die ganze Nacht als Geräusch zählt.
- **KI-Bewertung (optional):** ein Kamerabild über AI Task von Home Assistant mit fester Antwortstruktur, Budget, Zeitlimit und Ausweichkette. Die KI erreicht allein eine Warnung, einen kritischen Alarm erst nach einem bestätigenden zweiten Blick, und sie kann keinen Alarm aus einer anderen Quelle löschen oder herabstufen.
- **Atembewegungs-Hinweis (optional, standardmäßig im Schattenmodus):** eine Regel über eine Radar-Entität und die Vital-Engine.
- **Außerdem:** Ton-Weiterleitung auf einen Lautsprecher, Schlafsack-Empfehlung, Schlafprotokoll, Schnell-Check und Nachtbericht als Tasten und Aktionen, ein Sensor „Ruhezeit" und ein Alarm-Ereignis für eigene Automationen, Diagnose-Download.

Noch nicht gebaut sind unter anderem: ein geführter Funktionstest, eine Warnung vor einem Update, eine eigene Dashboard-Karte, Husten-Erkennung, eine Anbindung an Baby Buddy. Die vollständige Liste steht in Abschnitt 11 von [docs/MASTERPLAN.md](docs/MASTERPLAN.md).

## Voraussetzungen

- Home Assistant 2026.2 oder neuer, mit HACS
- Ein MQTT-Broker und die MQTT-Integration
- Frigate mit Audio-Erkennung für die Kamera am Bett; `crying` muss in dessen Liste `listen` ergänzt werden, weil es nicht zu Frigates Standard gehört
- Die Home-Assistant-App auf den Handys der Eltern
- Empfohlen: eine Sirene oder Lampe im Elternschlafzimmer als lokaler Alarm, der ohne Internet funktioniert

## Installation

1. In HACS `https://github.com/Puma7/HACheckBaby` als benutzerdefiniertes Repository vom Typ „Integration" hinzufügen.
2. „CheckBaby" herunterladen und Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → CheckBaby.
4. Mit stummgeschaltetem Handy die Taste „Testalarm" drücken und prüfen, dass er ertönt.

Die Schritte im Einzelnen, samt erstem Funktionstest, stehen unter [Installation](docs/de/installation.md).

## Dokumentation

| | |
|---|---|
| [Installation](docs/de/installation.md) | Voraussetzungen, Einrichtungsdialog, erster Funktionstest |
| [Frigate](docs/de/frigate.md) | MQTT-Themen, Frigate-Einstellungen, Betrieb ohne Frigate |
| [So funktioniert es](docs/de/how-it-works.md) | Zustände, Alarmstufen, Ausfallüberwachung, Privatmodus |
| [Entitäten und Aktionen](docs/de/entities-and-actions.md) | Jede Entität und jede Aktion |
| [KI-Bewertung](docs/de/ai-assessment.md) | Was die KI darf und was nicht, Einwilligung |
| [Vitalquellen](docs/de/vital-sources.md) | Der Atembewegungs-Hinweis und seine Grenzen |
| [Hardware](docs/de/hardware.md) | Kameras, Stückliste, Kabelsicherheit |
| [Sicherheit und Datenschutz](docs/de/safety-and-privacy.md) | Zweckbestimmung, sicherer Schlaf, Datenschutz |
| [Fehlersuche](docs/de/troubleshooting.md) | Störungen und Abhilfe |

Beispiele liegen in [docs/examples](docs/examples) und [blueprints](blueprints/automation/checkbaby).

## Entwicklung

Siehe [AGENTS.md](AGENTS.md) und die [Checkliste für die Prüfungen an echter Hardware](docs/development/phase-0-checkliste.md). Änderungen stehen in [CHANGELOG.md](CHANGELOG.md).

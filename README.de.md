# CheckBaby

Ein lokales Babyphone für Home Assistant auf Basis von Frigate, installiert über HACS. Es macht aus den Signalen von Frigate für Weinen, Geräuschpegel und Bewegung, aus optionalen Sensoren und einer optionalen KI-Bewertung einen Zustand des Kindes und Alarme in drei Stufen.

[English version](README.md) · [Dokumentation](docs/de/README.md) · [Documentation](docs/en/README.md)

**CheckBaby ist kein Medizinprodukt.** Es kann den plötzlichen Kindstod nicht verhindern und kann ohne Vorwarnung ausfallen. Es unterstützt deine Aufsicht und die Regeln für sicheren Babyschlaf, ersetzt aber beides nicht. Behalte ein einfaches Babyphone als Rückfallebene.

## Stand und Grenzen

Lies das, bevor du installierst. Die Versionsnummern folgen den Release-Tags (0.0.1, 0.0.2, …); HACS bietet ein Update an, sobald eine neue Version veröffentlicht ist.

- Die Integration ist durch automatische Tests abgedeckt, die gegen Home Assistant 2026.2 und 2026.10 laufen.
- Sie läuft außerdem in einem Labor ([lab/README.md](lab/README.md)): einem echten Home Assistant mit echtem MQTT-Broker, einem Frigate-Ersatz, simulierten Handys, Sensoren und simulierter Kamera, einem KI-Modell, das nach Drehbuch antwortet, und dem echten Prozess der Vital-Engine. Das Labor spielt Einrichtung, Alarmkette, Ausfälle und Neustarts in Echtzeit durch.
- **Eine erste Installation auf einem echten Home Assistant hat stattgefunden, und viel mehr noch nicht.** Sie hat zu den Korrekturen in Version 0.0.3 geführt: Handys werden jetzt mit Häkchen gewählt, weil ein im früheren Suchfeld gewähltes Handy nicht gespeichert wurde, und Alarme und Ergebnisse erscheinen zusätzlich in den Benachrichtigungen von Home Assistant selbst, damit auch ohne Handy etwas zu sehen ist.
- **Es gibt weiterhin keinen bestätigten Beleg, dass eine Push-Nachricht auf einem echten Handy ankommt** und trotz „Nicht stören" ertönt. Nichts ist bisher bekannt über die MQTT-Themen eines echten Frigate, darüber, ob ein echter KI-Anbieter (Gemini, OpenRouter, Ollama) das Kamerabild annimmt und gut beurteilt, oder über einen Radarsensor. Das Labor kann nichts davon zeigen. Ob es zu deinem System passt, zeigt der erste Abend.
- Die Vital-Engine (`engine/`) wurde nur mit künstlichen Signalen getestet und hat noch nie eine echte Kamera oder ein echtes Kind gesehen.
- Die Hardware-Beispiele (Frigate-Konfiguration, ESPHome für Radar und Summer, Blueprints) sind an echter Hardware ungetestet. Das englische Beispiel-Dashboard wurde im Labor geladen, das deutsche nicht.
- Der Atembewegungs-Hinweis ist an Säuglingen nicht validiert und standardmäßig ausgeschaltet. Er ist ein Hinweis, keine medizinische Messung.

## Was heute funktioniert

„Funktioniert" heißt: umgesetzt und durch die automatischen Tests und das Labor abgedeckt. Was Version 0.0.3 hinzufügt (Handys ankreuzen, die Benachrichtigungen von Home Assistant, der Zustellbericht), ist durch die automatischen Tests abgedeckt.

- **Einrichtung in der Oberfläche:** fünf kurze Seiten (Kind, Schlafplatz, wer benachrichtigt wird, optional die KI-Bewertung, Hinweis zur Zweckbestimmung), danach ein Schalter und eine Testtaste. Die Handys werden in einer Liste der Geräte mit der Home-Assistant-App angekreuzt; nichts muss eingetippt werden. Mehrere Schlafplätze je Kind, mehrere Kinder.
- **Quellen:** Frigate über MQTT (Weinen, Schrei, Geräuschpegel, Bewegung, Person, Katze oder Hund in der Bett-Zone, Verfügbarkeit) oder einfache Entitäten für Weinen, Bewegung und Pegel. Optional Türkontakt, Präsenz im Bett, Raumklima, Rauch/CO, Internetverbindung.
- **Zustand des Kindes:** schläft, unruhig, wach, weint, betreut, nicht im Bett, unbekannt. Wechsel folgen aus Dauern, nicht aus Einzelereignissen.
- **Alarme in drei Stufen:** Hinweis, Warnung, kritisch. Push-Nachrichten mit Kamerabild und den Knöpfen „Gesehen", „5 min Ruhe" und „Live"; kritische Alarme so gesendet, dass sie trotz „Nicht stören" ertönen, wiederholt alle 30 Sekunden; ein lokaler Alarm (Sirene, Licht) nach einer Minute; „Hat Dienst" und ein Babysitter-Modus mit eigenen Handys. Jede Warnung und jeder kritische Alarm erscheint zusätzlich in den Benachrichtigungen von Home Assistant selbst, und „Testalarm" schreibt dort einen Bericht, wohin der Alarm gegangen ist.
- **Ausfallüberwachung:** Jede Quelle wird überwacht, und ein Ausfall wird gemeldet, statt „schläft" anzuzeigen. Fällt nur das Bild, eine ungenutzte Vitalquelle oder ein Gerät des lokalen Alarms aus (solange ein Handy eingerichtet ist), erscheint das als Hinweis, ohne jemanden zu wecken. Meldungen beim Herunterfahren und nach einer Unterbrechung; optional ein Lebenszeichen für einen eigenen Ausfall-Summer („Dead-Man-Summer"), der ertönt, wenn Home Assistant verstummt.
- **Gelernter Grundpegel**, damit weißes Rauschen nicht die ganze Nacht als Geräusch zählt.
- **KI-Bewertung (optional):** Google Gemini, OpenRouter oder ein lokales Modell als eigene Home-Assistant-Integration hinzufügen, in CheckBaby auswählen und bestätigen; danach läuft sie von selbst. Ein Kamerabild über AI Task von Home Assistant mit fester Antwortstruktur, Budget, Zeitlimit und Ausweichkette. Die KI erreicht allein eine Warnung, einen kritischen Alarm erst nach einem bestätigenden zweiten Blick, und sie kann keinen Alarm aus einer anderen Quelle löschen oder herabstufen.
- **Atembewegungs-Hinweis (optional, standardmäßig im Schattenmodus):** eine Regel über eine Radar-Entität und die Vital-Engine.
- **Außerdem:** Ton-Weiterleitung auf einen Lautsprecher, Schlafsack-Empfehlung, Schlafprotokoll, Schnell-Check und Nachtbericht als Tasten und Aktionen, mit dem Ergebnis in den Benachrichtigungen von Home Assistant und auf dem Handy, ein Sensor „Ruhezeit" und ein Alarm-Ereignis für eigene Automationen, Diagnose-Download.

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
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → CheckBaby, dann fünf kurze Seiten ausfüllen.
4. Auf der Geräteseite mit stummgeschaltetem Handy „Testalarm" drücken und prüfen, dass er ertönt. Die Glocke in Home Assistant zeigt danach, wohin der Alarm gegangen ist. „Überwachung" einschalten, wenn das Kind schläft.

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

Siehe [AGENTS.md](AGENTS.md), das [Labor](lab/README.md) und die [Checkliste für die Prüfungen an echter Hardware](docs/development/phase-0-checkliste.md). Änderungen stehen in [CHANGELOG.md](CHANGELOG.md).

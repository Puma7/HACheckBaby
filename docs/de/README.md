# CheckBaby-Dokumentation

[English version](../en/README.md)

CheckBaby ist eine Home-Assistant-Integration, die aus Signalen von Frigate, optionalen Sensoren und einer optionalen KI-Bewertung ein Babyphone macht. **Es ist kein Medizinprodukt.** Es unterstützt deine Aufsicht und die Regeln für sicheren Babyschlaf, ersetzt aber beides nicht.

**Stand dieser Dokumentation.** Jede Seite beschreibt, was der Code heute tut. Die Integration ist durch automatische Tests abgedeckt und läuft in einem Labor mit einem echten Home Assistant und simulierten Geräten. Eine erste Installation auf einem echten Home Assistant hat stattgefunden; noch nicht bestätigt ist, dass eine Push-Nachricht auf einem echten Handy ankommt, und über ein echtes Frigate, einen echten KI-Anbieter oder einen Radarsensor ist noch nichts bekannt. Wo sich eine Seite auf die Dokumentation von Frigate, ESPHome oder der Home-Assistant-App stützt statt auf eigene Messungen, steht das dabei.

## Seiten

| Seite | Inhalt |
|---|---|
| [Installation](installation.md) | Voraussetzungen, Installation über HACS, der Einrichtungsdialog Schritt für Schritt, der erste Funktionstest |
| [Frigate](frigate.md) | Was CheckBaby per MQTT aus Frigate liest, welche Frigate-Einstellungen es braucht und wie es ohne Frigate geht |
| [So funktioniert es](how-it-works.md) | Zustände des Kindes, die drei Alarmstufen, wo ein Alarm ankommt (Handy, Benachrichtigungen von Home Assistant, lokaler Alarm, Wanddisplays), Quittieren und Schlummern, wer Dienst hat, Modi, Ausfallüberwachung, gelernter Grundpegel, Privatmodus, Neustarts |
| [Entitäten und Aktionen](entities-and-actions.md) | Jede Entität und jede Aktion mit Feldern und Rückgabewerten |
| [KI-Bewertung](ai-assessment.md) | Was eine KI-Aufgabe ist, das Einrichten, was die KI gefragt wird, wann, was sie darf und was nicht, Einwilligung und Datenschutz |
| [Vitalquellen](vital-sources.md) | Der Atembewegungs-Hinweis: Radarsensor, Vital-Engine, die Regel, Schattenmodus, bekannte Grenzen |
| [Hardware](hardware.md) | Kamera-Kandidaten, die Kauffalle, Stückliste, Montage und Kabelsicherheit |
| [Sicherheit und Datenschutz](safety-and-privacy.md) | Zweckbestimmung und Grenzen, Grundregeln für sicheren Schlaf, Netztrennung, Cloud-KI, Aufnahmen anderer Personen |
| [Fehlersuche](troubleshooting.md) | Jede Störung und jeder Reparaturhinweis mit Ursache und Abhilfe; keine Benachrichtigung auf dem Handy; stumme kritische Alarme; nicht erkanntes Weinen |

## Beispiele

Alle Beispiele sind an echter Hardware ungetestet. Jede Datei sagt das am Anfang und erklärt, was du anpassen musst. Die Kommentare in den Dateien sind englisch, außer im deutschen Dashboard.

| Datei | Was sie ist |
|---|---|
| [`dashboard.de.yaml`](../examples/dashboard.de.yaml) | Dashboard-Ansicht aus Standardkarten für ein Home Assistant mit deutscher Spracheinstellung |
| [`dashboard.yaml`](../examples/dashboard.yaml) | Dieselbe Ansicht für ein Home Assistant mit englischer Spracheinstellung, im Labor mit simulierten Geräten geladen (die Entitäts-IDs unterscheiden sich, siehe [Entitäten und Aktionen](entities-and-actions.md#entitäts-ids-hängen-von-der-sprache-ab)) |
| [`frigate-camera.yaml`](../examples/frigate-camera.yaml) | Frigate-Kameraabschnitt mit Audio-Erkennung für Weinen |
| [`esphome-mr60bha2.yaml`](../examples/esphome-mr60bha2.yaml) | ESPHome-Konfiguration für das Radar-Kit Seeed MR60BHA2 |
| [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml) | Ausfall-Summer („Dead-Man-Summer"): ein ESP32 mit Summer, der ertönt, wenn Home Assistant sein Lebenszeichen nicht mehr sendet |
| [`quiet_house.yaml`](../../blueprints/automation/checkbaby/quiet_house.yaml) | Automations-Vorlage: Aktionen ausführen, solange das Kind schläft und wenn es aufwacht |
| [`alert_light.yaml`](../../blueprints/automation/checkbaby/alert_light.yaml) | Automations-Vorlage: Eine Lampe zeigt Warnungen und kritische Alarme farbig an |

Der Plan hinter dem Projekt, einschließlich dessen, was noch nicht gebaut ist, steht in [MASTERPLAN.md](../MASTERPLAN.md).

# CheckBaby-Dokumentation

[English version](../en/README.md)

CheckBaby ist eine Home-Assistant-Integration, die aus Signalen von Frigate, optionalen Sensoren und einer optionalen KI-Bewertung ein Babyphone macht. **Es ist kein Medizinprodukt.** Es unterstützt deine Aufsicht und die Regeln für sicheren Babyschlaf, ersetzt aber beides nicht.

**Stand dieser Dokumentation.** Jede Seite beschreibt, was der Code heute tut. Die Integration ist durch automatische Tests abgedeckt, lief aber noch nie an einer echten Kamera, einem echten Frigate, einem Handy oder einem Radarsensor. Wo sich eine Seite auf die Dokumentation von Frigate, ESPHome oder der Home-Assistant-App stützt statt auf eigene Messungen, steht das dabei.

## Seiten

| Seite | Inhalt |
|---|---|
| [Installation](installation.md) | Voraussetzungen, Installation über HACS, der Einrichtungsdialog Schritt für Schritt, der erste Funktionstest |
| [Frigate](frigate.md) | Was CheckBaby per MQTT aus Frigate liest, welche Frigate-Einstellungen es braucht und wie es ohne Frigate geht |
| [So funktioniert es](how-it-works.md) | Zustände des Kindes, die drei Alarmstufen, Quittieren und Schlummern, wer Dienst hat, Modi, Ausfallüberwachung, gelernter Grundpegel, Privatmodus, Neustarts |
| [Entitäten und Aktionen](entities-and-actions.md) | Jede Entität und jede Aktion mit Feldern und Rückgabewerten |
| [KI-Bewertung](ai-assessment.md) | Was die KI gefragt wird, wann, was sie darf und was nicht, Einwilligung und Datenschutz |
| [Vitalquellen](vital-sources.md) | Der Atembewegungs-Hinweis: Radarsensor, Vital-Engine, die Regel, Schattenmodus, bekannte Grenzen |
| [Hardware](hardware.md) | Kamera-Kandidaten, die Kauffalle, Stückliste, Montage und Kabelsicherheit |
| [Sicherheit und Datenschutz](safety-and-privacy.md) | Zweckbestimmung und Grenzen, Grundregeln für sicheren Schlaf, Netztrennung, Cloud-KI, Aufnahmen anderer Personen |
| [Fehlersuche](troubleshooting.md) | Jede Störung und jeder Reparaturhinweis mit Ursache und Abhilfe; fehlende Benachrichtigungen; stumme kritische Alarme; nicht erkanntes Weinen |

## Beispiele

Alle Beispiele sind an echter Hardware ungetestet. Jede Datei sagt das am Anfang und erklärt, was du anpassen musst. Die Kommentare in den Dateien sind englisch, außer im deutschen Dashboard.

| Datei | Was sie ist |
|---|---|
| [`dashboard.de.yaml`](../examples/dashboard.de.yaml) | Dashboard-Ansicht aus Standardkarten für ein Home Assistant mit deutscher Spracheinstellung |
| [`dashboard.yaml`](../examples/dashboard.yaml) | Dieselbe Ansicht für ein Home Assistant mit englischer Spracheinstellung (die Entitäts-IDs unterscheiden sich, siehe [Entitäten und Aktionen](entities-and-actions.md#entitäts-ids-hängen-von-der-sprache-ab)) |
| [`frigate-camera.yaml`](../examples/frigate-camera.yaml) | Frigate-Kameraabschnitt mit Audio-Erkennung für Weinen |
| [`esphome-mr60bha2.yaml`](../examples/esphome-mr60bha2.yaml) | ESPHome-Konfiguration für das Radar-Kit Seeed MR60BHA2 |
| [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml) | ESP32 mit Summer, der ertönt, wenn Home Assistant keinen Herzschlag mehr sendet |
| [`quiet_house.yaml`](../../blueprints/automation/checkbaby/quiet_house.yaml) | Automations-Vorlage: Aktionen ausführen, solange das Kind schläft und wenn es aufwacht |
| [`alert_light.yaml`](../../blueprints/automation/checkbaby/alert_light.yaml) | Automations-Vorlage: Eine Lampe zeigt Warnungen und kritische Alarme farbig an |

Der Plan hinter dem Projekt, einschließlich dessen, was noch nicht gebaut ist, steht in [MASTERPLAN.md](../MASTERPLAN.md).

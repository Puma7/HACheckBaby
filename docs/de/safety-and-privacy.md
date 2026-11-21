# Sicherheit und Datenschutz

[English version](../en/safety-and-privacy.md) · [Zurück zur Übersicht](README.md)

## Zweckbestimmung

CheckBaby ist ein Aufmerksamkeits- und Komfortsystem für Eltern. Es sagt dir, wenn dein Kind weint, wenn einem KI-Modell etwas im Bett falsch vorkommt, wenn der Raum zu warm oder zu kalt ist und wenn seine eigene Überwachung ausgefallen ist.

**CheckBaby ist kein Medizinprodukt.** Es stellt keine Diagnose und garantiert keine Erkennung.

- **Es kann den plötzlichen Kindstod nicht verhindern.** Für kein Überwachungsgerät ist das belegt. Die American Academy of Pediatrics rät in ihrer Empfehlung von 2022 davon ab, Heimmonitore als Strategie zur Senkung dieses Risikos einzusetzen. Sie zu nutzen ist nicht schädlich, ersetzt aber nicht die Maßnahmen, die nachweislich helfen.
- **Es kann ohne Vorwarnung ausfallen.** Es hängt an einer Kamera, am WLAN, an Frigate, an einem MQTT-Broker, an Home Assistant, an deinem Handy und meist am Internet. Die Ausfallüberwachung meldet viele Ausfälle, aber nicht den Ausfall von Home Assistant selbst, solange du den Dead-Man-Summer nicht baust, und kein ausgeschaltetes Handy.
- **Es kann sich in beide Richtungen irren.** Weinen kann unerkannt bleiben, und Alarme können falsch sein. Die KI-Bewertung kann ein Bild überzeugend und falsch beschreiben.
- **Der Atembewegungs-Hinweis ist an Säuglingen nicht validiert** und standardmäßig ausgeschaltet. Siehe [Vitalquellen](vital-sources.md).
- **Es lief noch nicht an echter Hardware.** Die Integration ist durch automatische Tests abgedeckt; die Prüfungen mit echter Kamera, echtem Handy und echtem Sensor stehen noch aus.

Was daraus für dich folgt:

- Behalte ein einfaches Babyphone als Rückfallebene, mindestens bis CheckBaby zwei Wochen daneben gelaufen ist, ohne ein Weinen zu verpassen und ohne unbemerkt auszufallen.
- Lass ein stilles Handy nie das Nachsehen bei deinem Kind ersetzen.
- Wiederhole den Testalarm regelmäßig.
- Es ist keine Reiselösung. Unterwegs bleibt ein einfaches Gerät die vernünftige Wahl.

Das Projekt sagt bewusst „Atembewegungs-Hinweis". Software, die mit dem Zweck beworben wird, physiologische Vorgänge zu überwachen oder Krankheiten zu verhindern, kann unter die EU-Medizinprodukteverordnung fallen. Eine rechtliche Prüfung der Zweckbestimmung ist vor Version 1.0 geplant und hat noch nicht stattgefunden.

## Grundregeln für sicheren Schlaf

Das sind die Maßnahmen, hinter denen Belege stehen. Kein Gerät ersetzt sie.

- Lege dein Baby zum Schlafen **auf den Rücken**.
- Nimm eine **feste, flache** Unterlage.
- Lass das Baby im **eigenen Bett in deinem Zimmer** schlafen.
- **Keine losen Decken, Kissen oder Kuscheltiere** im Bett.
- Baby und Raum **nicht überwärmen**.
- Halte die Umgebung **rauchfrei**.

Diese Liste ist eine kurze Zusammenfassung und keine medizinische Beratung. Für Fragen zu deinem Kind sind Hebamme oder Kinderarztpraxis die richtige Adresse.

CheckBaby kann einige dieser Punkte unterstützen, wenn du die optionalen Teile nutzt: Die KI-Bewertung kann auf Bauchlage, ein verdecktes Gesicht und lose Gegenstände im Bett hinweisen, und die Raumtemperatur wird gegen den Bereich geprüft, den du einstellst. Das sind Hinweise eines Systems, das sich irren kann. Eine leere Hinweisliste heißt nicht, dass das Bett sicher ist.

Kabel und Geräte in der Nähe des Bettes sind eine Gefahr für sich; siehe [Hardware](hardware.md#montage-und-kabelsicherheit).

## Datenschutz

### Wo die Daten liegen

Alles wird bei dir zu Hause verarbeitet, mit einer Ausnahme, die du selbst einschalten musst: die KI-Bewertung bei einem Cloud-Anbieter.

| Daten | Wo sie liegen |
|---|---|
| Kamerabild und Ton | In der Kamera, in Frigate und in Home Assistant. Aufzeichnung und Aufbewahrung sind Einstellungen von Frigate; CheckBaby zeichnet nichts auf. |
| Name und Geburtsdatum des Kindes | In der Konfiguration von Home Assistant. |
| Einstellungen, aktive Alarme, Schlafprotokoll, gelernter Grundpegel | In einer Datei im Speicherordner von Home Assistant. Wird gelöscht, wenn du den Eintrag entfernst. |
| Ereignisprotokoll (die letzten 300 Entscheidungen mit ihrer Ursache) | Nur im Arbeitsspeicher; bei einem Neustart verloren. Im Diagnose-Download enthalten. |
| Bilder für die KI-Bewertung | Werden von CheckBaby nicht gespeichert. Werden an die KI-Aufgabe gesendet, die du gewählt hast. |

Den Verlauf der Sensoren bewahrt der Recorder von Home Assistant auf wie bei jeder anderen Entität.

### Keine Telemetrie

CheckBaby sendet nichts an das Projekt oder an Dritte, und der Code enthält keinen eigenen Netzzugriff. Die einzigen Daten, die dein Zuhause über CheckBaby verlassen können, sind die Benachrichtigungen an deine Handys und, wenn du es einschaltest, die Bilder für eine Cloud-KI.

### Die Kamera vom Internet fernhalten

- Gib der Kamera **keinen Internetzugang**: eine Firewall-Regel oder ein eigenes Netzsegment.
- Richte **keine Portfreigaben** zur Kamera oder zu Frigate ein.
- Bewahre die RTSP-Zugangsdaten **nur in Frigate** auf.
- Greife von außen **nur über deinen gesicherten Home-Assistant-Zugang** auf das Bild zu.

### Bilder in Benachrichtigungen

Hat der Schlafplatz eine Kamera-Entität, enthält jede Alarm-Benachrichtigung ein aktuelles Bild. Das Handy lädt es von deinem Home Assistant; von unterwegs braucht es dafür deine externe Adresse. Das Bild kann auf dem Sperrbildschirm erscheinen. Eine Option, das Bild wegzulassen, ist geplant, aber nicht umgesetzt: Um gar keine Bilder zu senden, lass das Feld „Kamera-Entität" leer; damit entfällt auch die KI-Bewertung.

Push-Nachrichten laufen normalerweise über die Server von Apple oder Google.

### Cloud-KI braucht deine Einwilligung

Bei einem Cloud-Anbieter verlässt mit jeder Bewertung ein Bild deines Kindes und seines Bettes dein Zuhause. CheckBaby sendet kein Bild, bevor du in den Optionen „Bilder des Kindes dürfen an diese KI-Aufgaben gesendet werden" angekreuzt hast. Je nach Tarif kann ein Anbieter Bilder zum Training verwenden; lies seine Bedingungen. Ein lokales Modell behält die Bilder im Haus. Einzelheiten stehen unter [KI-Bewertung](ai-assessment.md#datenschutz-und-einwilligung).

### Eine Kamera im eigenen Schlafzimmer

In den ersten Monaten schläft das Kind meist im Elternschlafzimmer, und damit hängt auch die Kamera dort.

- Nutze den **Privatmodus** für Momente vor der Kamera. Kenne seine Grenze: Er pausiert die Erkennung und die Benachrichtigungen von CheckBaby. Er schaltet weder die Kamera noch die Aufzeichnung von Frigate ab.
- Stelle Frigate für diese Kamera so ein, dass es **nichts oder nur kurz** aufzeichnet.

### Tonaufnahmen anderer Personen

Eine Kamera mit Mikrofon nimmt alle im Raum auf, nicht nur das Kind. In Deutschland ist das heimliche Aufzeichnen nichtöffentlicher Gespräche strafbar (§ 201 StGB). Babysitter, Großeltern und Besuch müssen wissen, dass Kamera und Mikrofon laufen. Sag es ihnen, bevor sie im Raum sind.

Der Babysitter-Modus ändert, wer benachrichtigt wird und wie schnell. Einen solchen Hinweis zeigt er nicht von selbst; das Bescheidsagen liegt bei dir.

Das ist ein Hinweis, keine Rechtsberatung. Andere Länder haben eigene Regeln.

### Der Diagnose-Download

Der Diagnose-Download entfernt den Namen des Kindes, das Geburtsdatum, die Adresse des Ton-Streams, die Namen der Schlafplätze und die Sätze der KI. Die Namen deiner Benachrichtigungsdienste und Entitäten enthält er. Lies ihn, bevor du ihn an einen öffentlichen Fehlerbericht hängst.

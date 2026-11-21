# Installation

[English version](../en/installation.md) · [Zurück zur Übersicht](README.md)

CheckBaby ist kein Medizinprodukt. Behalte ein einfaches Babyphone als Rückfallebene, mindestens bis du CheckBaby ein paar Wochen bei dir zu Hause hast arbeiten sehen.

Die Schritte unten folgen dem Code. Sie wurden noch nicht an einer echten Installation mit Kamera und Handy durchgespielt. Behandle den ersten Abend deshalb als Test.

## Was du brauchst

| Voraussetzung | Warum |
|---|---|
| Home Assistant 2026.2 oder neuer | Ältere Versionen sind nicht getestet, und HACS verweigert die Installation. |
| Ein MQTT-Broker und die MQTT-Integration in Home Assistant | Frigate veröffentlicht Weinen, Geräuschpegel und Bewegung per MQTT, und CheckBaby liest sie dort. |
| Frigate mit Audio-Erkennung für die Kamera am Bett | Es erkennt Weinen und meldet den Geräuschpegel. Siehe [Frigate](frigate.md). |
| Die Home-Assistant-App auf den Handys der Eltern | Alarme kommen als Benachrichtigungen der App. |
| HACS | CheckBaby wird als benutzerdefiniertes Repository installiert. |

Optional und jederzeit nachrüstbar: eine Sirene, eine Lampe oder ein Schalter als lokaler Alarm im Elternschlafzimmer; ein Türkontakt; ein Präsenzsensor für das Bett; ein Temperatur- und Feuchtesensor; ein Radarsensor, der eine Atemrate meldet; eine KI-Aufgabe (AI Task); Rauch- und CO-Melder; ein Sensor, der anzeigt, ob die Internetverbindung steht.

CheckBaby läuft auch ohne Frigate, wenn ein anderes Gerät dir einen Binärsensor liefert, der an ist, solange das Kind weint. Siehe [Frigate](frigate.md#ohne-frigate).

## Über HACS installieren

1. Öffne HACS in Home Assistant.
2. Öffne oben rechts das Menü und wähle **Benutzerdefinierte Repositories**.
3. Trage `https://github.com/Puma7/HACheckBaby` ein, wähle den Typ **Integration** und füge es hinzu.
4. Suche in HACS nach **CheckBaby**, öffne es und wähle **Herunterladen**.
5. Starte Home Assistant neu.

## Der Einrichtungsdialog

Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und wähle **CheckBaby**. Der Dialog hat vier Schritte. Angelegt wird erst etwas, wenn du den letzten bestätigst.

### Schritt 1: das Kind

| Feld | Was du einträgst |
|---|---|
| Name des Kindes | Wird für das Gerät, die Namen der Entitäten und die Benachrichtigungstexte verwendet. Jedes Kind ist ein Eintrag; ein zweiter Eintrag mit demselben Namen wird abgelehnt. |
| Geburtsdatum oder errechneter Termin | Bestimmt das Altersprofil (Neugeborenes bis etwa drei Monate, Säugling bis ein Jahr, danach Kleinkind). Du kannst CheckBaby schon vor der Geburt mit dem errechneten Termin einrichten. |

Das Altersprofil ändert derzeit zwei Dinge: wie eine von der KI-Bewertung gemeldete Bauchlage behandelt wird, und ob ein Kind, das das Bett allein verlässt, eine Warnung auslöst (nur beim Kleinkind). Die übrigen Schwellen starten für jedes Alter mit denselben Werten, und du passt sie selbst an.

### Schritt 2: der Schlafplatz

Ein Schlafplatz ist ein Bett mit seiner Kamera und seinen Sensoren. Du brauchst einen Namen und eine Tonquelle: entweder den Namen der Frigate-Kamera oder einen Wein-Sensor. Alles andere ist optional.

| Feld | Was du einträgst |
|---|---|
| Name des Schlafplatzes | Zum Beispiel „Beistellbett". |
| Name der Frigate-Kamera | Der Name der Kamera in der Frigate-Konfiguration, zum Beispiel `kinderzimmer`. Weinen, Geräuschpegel und Bewegung kommen per MQTT aus Frigate. |
| Kamera-Entität | Die Kamera-Entität in Home Assistant. Sie liefert das Bild in Benachrichtigungen und das Bild für die KI-Bewertung. |
| Frigate-Zone des Bettes | Wenn gesetzt, löst eine Katze oder ein Hund, die Frigate in dieser Zone sieht, eine Warnung aus. |
| Türkontakt | Solange die Tür offen ist, gilt jemand als beim Kind, und die kindbezogenen Alarme pausieren. |
| Eine von der Kamera erkannte Person zählt als Betreuung | Nur einschalten, wenn Frigate das Kind nicht selbst als Person erkennt. |
| Präsenzsensor für das Bett | Ein Binärsensor, der an ist, solange das Kind im Bett liegt. |
| Raumtemperatur, Luftfeuchte | Werden am Gerät angezeigt; die Temperatur wird zusätzlich gegen den Bereich geprüft, den du einstellst. Der Sensor muss Grad Celsius melden. |
| Atemraten-Sensor (Radar), Herzraten-Sensor (Radar) | Siehe [Vitalquellen](vital-sources.md). |
| ID der Vital-Engine | Nur mit der CheckBaby-Vital-Engine, siehe [Vitalquellen](vital-sources.md). |
| Adresse des Ton-Streams | Wird von der Ton-Weiterleitung auf einem Lautsprecher abgespielt, zum Beispiel ein Ton-Stream aus go2rtc. |
| Wein-Sensor, Bewegungssensor, Geräuschpegel-Sensor | Die Alternative zu Frigate. Fülle sie nicht zusammen mit dem Namen einer Frigate-Kamera aus. |

### Schritt 3: wer benachrichtigt wird

| Feld | Was du einträgst |
|---|---|
| Handys | Die Benachrichtigungsdienste der Home-Assistant-App, zum Beispiel `mobile_app_annas_iphone`. Die Liste bietet jeden Dienst an, der mit `mobile_app_` beginnt; du kannst auch den Namen eines anderen Benachrichtigungsdienstes eintippen. |
| Lokaler Alarm (Sirene, Licht, Schalter) | Wird eingeschaltet, wenn ein Alarm eine Minute unbeantwortet bleibt, oder sofort, solange das Internet ausgefallen ist. Gehört ins Elternschlafzimmer, nie ins Kinderzimmer. |

Du musst mindestens ein Handy oder einen lokalen Alarm wählen. Ohne eines von beiden könnte kein Alarm jemanden erreichen.

### Schritt 4: der Hinweis zur Zweckbestimmung

Der letzte Schritt zeigt, was CheckBaby ist und was nicht. Du musst „Ich habe das gelesen und verstanden" ankreuzen, um abzuschließen.

## Nach der Einrichtung

Das Gerät des Kindes erscheint mit seinen Entitäten. **Die Überwachung ist zunächst aus.** Schalte den Schalter **Überwachung** ein, wenn du Alarme möchtest.

Weitere Einstellungen stehen in den Optionen des Eintrags (**Konfigurieren**): das Handy des Babysitters, Herzschlag-Tasten für einen Dead-Man-Summer, Rauch- und CO-Melder, der Sensor für die Internetverbindung, der Lautsprecher für die Ton-Weiterleitung, die KI-Aufgaben samt Einwilligung zum Senden von Bildern, die KI-Aufrufe pro Stunde, das MQTT-Präfix von Frigate (Standard `frigate`) und das Dashboard, das eine Benachrichtigung öffnet (Standard `/lovelace`).

Weitere Schlafplätze fügst du am Eintrag mit **Schlafplatz hinzufügen** hinzu. Überwacht wird immer genau ein Schlafplatz; du wählst ihn mit der Auswahl **Aktiver Schlafplatz**.

Wenn du die Optionen oder einen Schlafplatz änderst, wird der Eintrag neu geladen. Einstellungen, aktive Alarme und das Schlafprotokoll bleiben dabei erhalten.

## Erster Funktionstest

Mach das, bevor du dich auf irgendetwas verlässt.

1. **Warte zwei Minuten** nach der Einrichtung. In dieser Zeit zählen Quellen, die sich noch nicht gemeldet haben, nicht als Störung.
2. **Prüfe die Ausfallüberwachung.** Der Binärsensor **Störung der Überwachung** muss aus sein. Ist er an, nennt der Sensor **Störungen der Überwachung** im Attribut `problems` die Gründe; die [Fehlersuche](troubleshooting.md) erklärt jeden.
3. **Stelle dein Handy stumm** und schalte „Nicht stören" ein. Das ist der Fall, auf den es nachts ankommt.
4. **Drücke die Taste „Testalarm"** auf der Geräteseite (sie steht unter „Diagnose"). Der Test funktioniert auch bei ausgeschalteter Überwachung.
5. **Prüfe, was ankommt.** Jedes eingerichtete Handy sollte eine Benachrichtigung mit dem Titel „ALARM · (Name)" und dem Text „Testalarm. Mit „Gesehen“ beenden." bekommen. Sie sollte ertönen, obwohl das Handy stumm ist. Wenn du eine Kamera-Entität eingetragen hast, enthält sie ein Bild.
6. **Warte.** Die Benachrichtigung wiederholt sich alle 30 Sekunden. Nach 60 Sekunden ohne Reaktion schaltet sich der lokale Alarm ein.
7. **Tippe in der Benachrichtigung auf „Gesehen".** Die Benachrichtigung verschwindet von allen Handys, und der lokale Alarm geht aus. Tippt niemand, endet der Test nach zehn Minuten von selbst.

Wenn der kritische Alarm nicht ertönt, lies [Fehlersuche](troubleshooting.md#ein-kritischer-alarm-ertönt-nicht).

Danach die echte Kette:

1. Schalte die **Überwachung** ein.
2. Spiele neben der Kamera eine Aufnahme eines weinenden Babys in realistischer Lautstärke ab.
3. Mit den Standardwerten wechselt der Zustand nach etwa 8 Sekunden erkanntem Weinen auf „Weint", und nach 15 Sekunden kommt eine Warnung. Die Verzögerung der Erkennung in Frigate kommt obendrauf.

Wiederhole den Testalarm von Zeit zu Zeit und nach jedem Update von Home Assistant, Frigate oder der Home-Assistant-App. Ein geführter Funktionstest mit monatlicher Erinnerung ist geplant, aber noch nicht umgesetzt.

## Dashboard und Automationen

- Ein Beispiel-Dashboard liegt in [`docs/examples/dashboard.de.yaml`](../examples/dashboard.de.yaml).
- Die beiden Automations-Vorlagen (Blueprints) liegen in [`blueprints/automation/checkbaby/`](../../blueprints/automation/checkbaby/). Kopiere sie auf deinem Home Assistant nach `config/blueprints/automation/checkbaby/`, oder nutze **Einstellungen → Automationen & Szenen → Blueprints → Blueprint importieren** mit der Adresse der Datei auf GitHub. HACS installiert keine Blueprints.

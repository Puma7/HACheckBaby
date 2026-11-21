# Installation

[English version](../en/installation.md) · [Zurück zur Übersicht](README.md)

CheckBaby ist kein Medizinprodukt. Behalte ein einfaches Babyphone als Rückfallebene, mindestens bis du CheckBaby ein paar Wochen bei dir zu Hause hast arbeiten sehen.

Die hier beschriebene Einrichtung wird in einem Labor durchgespielt: einem echten Home Assistant mit simulierter Kamera, simulierten Handys und Sensoren, eingerichtet über dieselbe Schnittstelle, die auch die Dialoge benutzen. Eine erste Installation auf einem echten Home Assistant hat stattgefunden; was sie gezeigt hat, hat zu Änderungen in dieser Version geführt (Handys werden mit Häkchen gewählt, und Ergebnisse sind in den Benachrichtigungen von Home Assistant zu sehen). Noch nicht bestätigt ist, dass eine Push-Nachricht auf einem echten Handy ankommt, und über ein echtes Frigate, einen echten KI-Anbieter oder einen Radarsensor ist noch nichts bekannt. Behandle den ersten Abend deshalb als Test.

## Der ganze Weg

1. CheckBaby über HACS installieren und Home Assistant neu starten.
2. Die Integration hinzufügen und fünf kurze Seiten ausfüllen.
3. **Überwachung** einschalten und einmal **Testalarm** drücken.

Mehr braucht es nicht. Alles Weitere auf dieser Seite erklärt diese drei Schritte. KI-Bewertung, Radarsensor, weitere Schlafplätze und ein Dashboard lassen sich später ergänzen.

## Bevor du anfängst

| Du brauchst | Warum |
|---|---|
| Home Assistant 2026.2 oder neuer, mit HACS | Ältere Versionen sind nicht getestet, und HACS verweigert die Installation. |
| Einen MQTT-Broker und die MQTT-Integration in Home Assistant | Frigate veröffentlicht Weinen, Geräuschpegel und Bewegung per MQTT, und CheckBaby liest sie dort. |
| Frigate mit Audio-Erkennung für die Kamera am Bett | Es erkennt Weinen und meldet den Geräuschpegel. Auf eine Einstellung kommt es an: `crying` muss in Frigates Liste `listen` ergänzt werden. Siehe [Frigate](frigate.md). |
| Die Home-Assistant-App auf den Handys der Eltern, an deinem Home Assistant angemeldet | Alarme kommen als Benachrichtigungen der App. Ein Handy taucht in CheckBaby erst auf, nachdem sich die App darauf angemeldet hat. |

Halte zwei Namen bereit, denn die Einrichtung fragt danach:

- den **Namen der Kamera in Frigate**, zum Beispiel `kinderzimmer`,
- die **Kamera-Entität in Home Assistant**, zum Beispiel `camera.kinderzimmer`.

Kein Frigate? CheckBaby läuft auch mit einem Binärsensor, der an ist, solange das Kind weint. Siehe [Frigate](frigate.md#ohne-frigate).

## Schritt 1: über HACS installieren

1. Öffne HACS in Home Assistant.
2. Öffne oben rechts das Menü und wähle **Benutzerdefinierte Repositories**.
3. Trage `https://github.com/Puma7/HACheckBaby` ein, wähle den Typ **Integration** und füge es hinzu.
4. Suche in HACS nach **CheckBaby**, öffne es und wähle **Herunterladen**.
5. Starte Home Assistant neu.

## Schritt 2: CheckBaby hinzufügen

Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und wähle **CheckBaby**. Es folgen fünf Seiten. Angelegt wird erst etwas, wenn du die letzte bestätigst.

### Seite 1: das Kind

| Feld | Was du einträgst |
|---|---|
| Name des Kindes | Wird für das Gerät, die Namen der Entitäten und die Benachrichtigungstexte verwendet. Jedes Kind ist ein Eintrag; ein zweiter Eintrag mit demselben Namen wird abgelehnt. |
| Geburtsdatum oder errechneter Termin | Bestimmt das Altersprofil (Neugeborenes bis etwa drei Monate, Säugling bis ein Jahr, danach Kleinkind). Du kannst CheckBaby schon vor der Geburt mit dem errechneten Termin einrichten. |

Das Altersprofil bestimmt, welche Alarme gelten: wie eine von der KI-Bewertung gemeldete Bauchlage behandelt wird, und ob ein Kind, das das Bett allein verlässt, eine Warnung auslöst (nur beim Kleinkind). Schwellen ändert es nicht.

### Seite 2: der Schlafplatz

Ein Schlafplatz ist ein Bett mit seiner Kamera und seinen Sensoren. **Fülle für den Anfang drei Felder aus und lass den Rest leer:**

| Feld | Was du einträgst |
|---|---|
| Name des Schlafplatzes | Zum Beispiel „Beistellbett". |
| Name der Frigate-Kamera | Der Name der Kamera in der Frigate-Konfiguration, zum Beispiel `kinderzimmer`. Weinen, Geräuschpegel und Bewegung kommen per MQTT aus Frigate. |
| Kamera-Entität | Die Kamera-Entität in Home Assistant. Sie liefert das Bild in Benachrichtigungen und das Bild für die KI-Bewertung. |

Pflicht sind nur der Name und eine Tonquelle (der Name der Frigate-Kamera oder ein Wein-Sensor). Alle anderen Felder sind optional und lassen sich später am Eintrag mit **Schlafplatz ändern** nachtragen:

| Optionales Feld | Was es bewirkt |
|---|---|
| Frigate-Zone des Bettes | Eine Katze oder ein Hund, die Frigate in dieser Zone sieht, löst eine Warnung aus. |
| Türkontakt | Solange die Tür offen ist, gilt jemand als beim Kind, und die kindbezogenen Alarme pausieren. |
| Eine von der Kamera erkannte Person zählt als Betreuung | Nur einschalten, wenn Frigate das Kind nicht selbst als Person erkennt. |
| Präsenzsensor für das Bett | Ein Binärsensor, der an ist, solange das Kind im Bett liegt. |
| Raumtemperatur, Luftfeuchte | Werden am Gerät angezeigt; die Temperatur wird zusätzlich gegen den Bereich geprüft, den du einstellst. Der Sensor darf Grad Celsius oder Fahrenheit melden; Fahrenheit wird vor dem Vergleich umgerechnet. |
| Atemraten-Sensor (Radar), Herzraten-Sensor (Radar), ID der Vital-Engine | Für den Atembewegungs-Hinweis, siehe [Vitalquellen](vital-sources.md). |
| Adresse des Ton-Streams | Wird von der Ton-Weiterleitung auf einem Lautsprecher abgespielt, zum Beispiel ein Ton-Stream aus go2rtc. |
| Wein-Sensor, Bewegungssensor, Geräuschpegel-Sensor | Die Alternative zu Frigate. Sie werden ignoriert, solange der Name einer Frigate-Kamera eingetragen ist. |

### Seite 3: wer benachrichtigt wird

| Feld | Was du einträgst |
|---|---|
| Handys | Jedes Handy mit der Home-Assistant-App steht mit seinem Gerätenamen in der Liste, mit einem Kästchen zum Ankreuzen. Kreuze die Handys der Eltern an; du musst nichts eintippen. Andere Benachrichtigungsdienste, zum Beispiel eine Benachrichtigungsgruppe, stehen als `notify.<name>` in der Liste. |
| Lokaler Alarm (Sirene, Licht, Schalter) | Optional, aber empfohlen: ein Gerät, das Home Assistant selbst schaltet. Es wird eingeschaltet, wenn ein Alarm eine Minute unbeantwortet bleibt, oder sofort, solange das Internet ausgefallen ist. Gehört ins Elternschlafzimmer, nie ins Kinderzimmer. Das Gerät muss in Home Assistant erreichbar sein: Eine Lampe, die am Wandschalter aus ist, bleibt dunkel. |

Du musst mindestens ein Handy ankreuzen oder einen lokalen Alarm wählen. Ohne eines von beiden könnte kein Alarm jemanden erreichen.

**Fehlt ein Handy in der Liste?** Öffne auf diesem Handy die Home-Assistant-App und melde dich an deinem Home Assistant an. Die Liste wird gelesen, wenn die Seite aufgeht; öffne die Seite danach also noch einmal.

**Das Handy ist der Hauptalarm.** Ein kritischer Alarm wird so gesendet, dass er trotz „Nicht stören" ertönt. Eine Push-Nachricht läuft normalerweise über die Server von Apple oder Google und braucht deshalb das Internet. Der lokale Alarm ist der Weg, der ganz ohne Internet funktioniert. Mehr zu beidem und zum Empfang von Benachrichtigungen über das Heimnetz steht unter [Wo ein Alarm ankommt](how-it-works.md#wo-ein-alarm-ankommt).

### Seite 4: KI-Bewertung (optional)

**Zum Überspringen lässt du die Seite leer und gehst weiter.** Alles andere funktioniert auch ohne, und du kannst später darauf zurückkommen.

Ein KI-Modell kann ein Kamerabild ansehen und sagen, ob das Kind auf dem Rücken liegt, ob das Gesicht frei ist und ob lose Dinge im Bett liegen. Wenn du das möchtest:

1. Das Modell selbst wird einmal in Home Assistant hinzugefügt, nicht in CheckBaby: **Einstellungen → Geräte & Dienste → Integration hinzufügen → Google Gemini** oder **OpenRouter**. Dort trägst du den API-Schlüssel ein. Ein lokales Modell über **Ollama** fügst du genauso hinzu. Hast du das noch nicht getan, überspringe diese Seite jetzt und hole es danach nach.
2. Wähle auf dieser Seite das Modell im Feld **KI-Modell (eine „KI-Aufgabe" von Home Assistant)**. Eine leere Liste bedeutet, dass noch keine KI-Integration eingerichtet ist.
3. Kreuze **Bilder des Kindes dürfen an diese KI-Aufgaben gesendet werden** an. Bei einem Cloud-Modell verlassen Bilder deines Kindes dein Zuhause; lies vorher [KI-Bewertung](ai-assessment.md#datenschutz-und-einwilligung).

Mehr ist nicht nötig. Von da an läuft die Bewertung von selbst, solange die Überwachung an ist.

### Seite 5: der Hinweis zur Zweckbestimmung

Die letzte Seite sagt, was CheckBaby ist und was nicht. Kreuze „Ich habe das gelesen und verstanden" an, um abzuschließen.

## Schritt 3: einschalten und testen

Home Assistant bestätigt die Einrichtung mit einem kurzen Hinweis: „Fertig. Zwei Dinge vor der ersten Nacht: Schalte auf der Geräteseite „Überwachung“ ein, wenn das Kind schläft, und drücke einmal „Testalarm“, um zu prüfen, dass der Alarm auf jedem Handy ankommt, auch stumm geschaltet." Das sind die zwei Dinge:

1. **Öffne das Gerät** des Kindes (Einstellungen → Geräte & Dienste → CheckBaby). **Die Überwachung ist zunächst aus.**
2. **Stelle dein Handy stumm** und schalte „Nicht stören" ein. Das ist der Fall, auf den es nachts ankommt.
3. **Drücke „Testalarm"** auf der Geräteseite (die Taste steht unter „Diagnose"). Der Test funktioniert auch bei ausgeschalteter Überwachung.
4. **Prüfe, was ankommt.** Jedes angekreuzte Handy sollte eine Benachrichtigung mit dem Titel „ALARM · (Name)" und dem Text „Testalarm. Mit „Gesehen“ beenden." bekommen. Sie sollte ertönen, obwohl das Handy stumm ist. Wenn du eine Kamera-Entität eingetragen hast, enthält sie ein Bild.
5. **Sieh bei der Glocke in Home Assistant nach** (die Benachrichtigungen in der Seitenleiste). Dort stehen zwei Einträge: der Testalarm selbst und ein Zustellbericht. Der Bericht sagt, wohin der Alarm gegangen ist: welche Benachrichtigungsdienste die Nachricht angenommen haben, welche nicht erreichbar waren und welche Geräte als lokaler Alarm eingetragen oder nicht erreichbar sind. Ist auf einem Handy nichts angekommen, fang hier an.
6. **Warte eine Minute**, wenn du einen lokalen Alarm gewählt hast. Die Benachrichtigung wiederholt sich alle 30 Sekunden, und nach 60 Sekunden ohne Reaktion schaltet sich der lokale Alarm ein.
7. **Tippe in der Benachrichtigung auf „Gesehen".** Die Benachrichtigung verschwindet von allen Handys und aus den Benachrichtigungen von Home Assistant, und der lokale Alarm geht aus. Der Zustellbericht bleibt stehen, bis du ihn wegklickst. Tippt niemand auf „Gesehen", endet der Test nach zehn Minuten von selbst.
8. **Schalte „Überwachung" ein**, wenn das Kind schläft.

Wenn keine Benachrichtigung ankommt, lies [Fehlersuche](troubleshooting.md#auf-dem-handy-kommt-keine-benachrichtigung-an). Wenn der kritische Alarm ankommt, aber nicht ertönt, lies [Fehlersuche](troubleshooting.md#ein-kritischer-alarm-ertönt-nicht).

Sieh zwei Minuten nach der Einrichtung auf der Geräteseite nach dem Binärsensor **Störung der Überwachung**. Er muss aus sein. Ist er an, nennt der Sensor **Störungen der Überwachung** die Gründe, und die [Fehlersuche](troubleshooting.md) erklärt jeden.

## Schritt 4: mit echtem Weinen testen

1. Stelle sicher, dass die **Überwachung** an ist.
2. Spiele neben der Kamera eine Aufnahme eines weinenden Babys in realistischer Lautstärke ab.
3. Mit den Standardwerten wechselt der Zustand nach etwa 8 Sekunden erkanntem Weinen auf „Weint", und nach 15 Sekunden kommt eine Warnung. Die Verzögerung der Erkennung in Frigate kommt obendrauf.

Wiederhole den Testalarm von Zeit zu Zeit und nach jedem Update von Home Assistant, Frigate oder der Home-Assistant-App. Ein geführter Funktionstest mit monatlicher Erinnerung ist geplant, aber noch nicht umgesetzt.

## Später, wenn du es brauchst

### Eine Einstellung ändern

Gehe zu **Einstellungen → Geräte & Dienste → CheckBaby** und wähle **Konfigurieren**. Es öffnet sich ein Menü mit drei kurzen Seiten. Speicherst du eine Seite, bleiben die Einstellungen der anderen beiden erhalten.

| Seite | Was darauf steht |
|---|---|
| Wer benachrichtigt wird | Handys, lokaler Alarm, Handys der Babysitter, Lebenszeichen für einen Ausfall-Summer |
| KI-Bewertung | KI-Modell (eine „KI-Aufgabe" von Home Assistant), die Einwilligung zum Senden von Bildern, KI-Aufrufe pro Stunde höchstens (Standard 30) |
| Weitere Geräte und Einstellungen | Rauch- und CO-Melder, Sensor für die Internetverbindung, Lautsprecher für die Ton-Weiterleitung, MQTT-Präfix von Frigate (Standard `frigate`), Dashboard, das eine Benachrichtigung öffnet (Standard `/lovelace`) |

Die Seite „Wer benachrichtigt wird" hat zwei Felder, nach denen die Einrichtung nicht fragt:

- **Handys der Babysitter:** Kästchen zum Ankreuzen wie bei „Handys", zum Beispiel für Großeltern oder einen Babysitter. Diese Handys bekommen Alarme nur, solange der Modus auf „Babysitter" steht, zusätzlich zu den Handys, die unter „Handys" angekreuzt sind. Ist ein Handy nur hier angekreuzt und weder ein Handy unter „Handys" noch ein lokaler Alarm gewählt, wird die Seite mit einer eigenen Meldung abgelehnt, weil dieses Handy nur im Babysitter-Modus benachrichtigt würde.
- **Lebenszeichen für einen Ausfall-Summer (optional):** Lass das leer, wenn du keinen Ausfall-Summer (auch „Dead-Man-Summer" genannt) gebaut hast. Das ist ein kleines eigenes Gerät, das piept, sobald Home Assistant verstummt, zum Beispiel nach einem Absturz oder wenn Strom oder WLAN ausfallen. CheckBaby drückt die hier gewählte Taste alle 30 Sekunden als Lebenszeichen, solange die Überwachung an ist und funktioniert. Ein Baubeispiel für einen ESP32 liegt in [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml).

Ein Handy oder Benachrichtigungsdienst, der früher angekreuzt wurde und in Home Assistant nicht mehr existiert, bleibt mit einem „?" hinter dem Namen in der Liste, damit du das Häkchen entfernen kannst.

Die Schwellen und Schalter (zum Beispiel, wie lange Weinen bis zur Warnung dauert) stehen nicht in diesem Menü. Sie sind Entitäten auf der Geräteseite, siehe [Entitäten und Aktionen](entities-and-actions.md).

### Die KI-Bewertung nachträglich einrichten

Füge die Integration des Modells hinzu, wie unter Seite 4 beschrieben, öffne dann **Konfigurieren → KI-Bewertung**, wähle das Modell und setze das Häkchen für die Einwilligung. Drücke danach auf der Geräteseite „KI-Check jetzt": Das Ergebnis erscheint in den Benachrichtigungen von Home Assistant. Einzelheiten stehen unter [KI-Bewertung](ai-assessment.md#einrichten).

### Weitere Schlafplätze

Nimm **Schlafplatz hinzufügen** am CheckBaby-Eintrag und **Schlafplatz ändern**, um einen zu bearbeiten. Überwacht wird immer genau ein Schlafplatz; du wählst ihn mit der Auswahl **Aktiver Schlafplatz** auf der Geräteseite.

Wenn du eine Einstellung oder einen Schlafplatz änderst, wird der Eintrag neu geladen. Deine Einstellungen, aktive Alarme und das Schlafprotokoll bleiben dabei erhalten.

### Dashboard und Automationen

- Ein Beispiel-Dashboard liegt in [`docs/examples/dashboard.de.yaml`](../examples/dashboard.de.yaml). Die Datei erklärt am Anfang, wie du sie verwendest.
- Zwei Automations-Vorlagen (Blueprints) liegen in [`blueprints/automation/checkbaby/`](../../blueprints/automation/checkbaby/). Kopiere sie auf deinem Home Assistant nach `config/blueprints/automation/checkbaby/`, oder nutze **Einstellungen → Automationen & Szenen → Blueprints → Blueprint importieren** mit der Adresse der Datei auf GitHub. HACS installiert keine Blueprints.

### Updates

HACS bietet ein Update an, sobald eine neue Version von CheckBaby auf GitHub veröffentlicht ist. Die Versionsnummern folgen den Release-Tags (0.0.1, 0.0.2, …). Wiederhole nach jedem Update den Testalarm.

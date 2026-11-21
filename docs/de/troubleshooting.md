# Fehlersuche

[English version](../en/troubleshooting.md) · [Zurück zur Übersicht](README.md)

Fang an zwei Stellen an:

- Beim Sensor **Störungen der Überwachung** am Gerät. Sein Attribut `problems` nennt, was die Ausfallüberwachung gefunden hat.
- Unter **Einstellungen → System → Reparaturen** bei den drei Reparaturhinweisen.

Bei allem Unerwarteten hilft **Diagnose herunterladen** am CheckBaby-Eintrag. Die Datei enthält das Ereignisprotokoll mit der Ursache jeder Entscheidung.

CheckBaby wurde bisher ein einziges Mal auf einem echten Home Assistant installiert. Zu einem echten Frigate, einer Push-Nachricht auf einem echten Handy, einem echten KI-Anbieter oder einem Radarsensor ist noch nichts bestätigt; eine Abweichung zu jedem davon ist deshalb gut möglich. Verhält sich etwas nicht wie hier beschrieben, sind das MQTT-Thema mit Nutzlast oder die Fehlermeldung aus dem Home-Assistant-Protokoll die wichtigsten Angaben für einen Fehlerbericht.

## Störungen der Überwachung

Die Namen sind die aus dem Attribut `problems`. In einer Benachrichtigung stehen sie in Worten.

| Störung | In der Benachrichtigung | Ursache | Was tun |
|---|---|---|---|
| `mqtt` | MQTT getrennt | Die MQTT-Integration ist nicht geladen oder hat den Broker verloren. | Prüfe den Broker und die MQTT-Integration. CheckBaby abonniert von selbst, sobald MQTT zurück ist. |
| `frigate` | Frigate offline | `<präfix>/available` meldet nicht `online`, oder dort kam in den zwei Minuten nach dem Start nichts an. | Prüfe, ob Frigate läuft, ob MQTT in Frigate eingeschaltet ist und ob das MQTT-Präfix in den CheckBaby-Optionen zu Frigates `topic_prefix` passt. |
| `audio_level` | kein Ton von der Kamera | Länger als 60 Sekunden kein Wert auf `<präfix>/<kamera>/audio/dBFS`. Ohne Frigate: Der Geräuschpegel-Sensor hat keinen Zahlenwert. | Prüfe, ob der Stream eine Tonspur hat, ob der Eingang die Rolle `audio` hat, ob die Audio-Erkennung für diese Kamera eingeschaltet ist und ob der „Name der Frigate-Kamera" genau so geschrieben ist wie in Frigate. |
| `microphone` | Mikrofonsignal flach | Pegel kommen an, aber der Wert hat sich 10 Minuten lang überhaupt nicht verändert. | Das Mikrofon kann tot oder in den Einstellungen der Kamera stummgeschaltet sein. Hör in den Stream hinein. Diese Prüfung gilt nur für den Pegel aus Frigate, nicht für eine Geräuschpegel-Sensor-Entität. |
| `cry_sensor` | Wein-Sensor nicht verfügbar | Ohne Frigate: Der Wein-Sensor ist nicht verfügbar oder unbekannt. | Prüfe das Gerät, das ihn liefert. |
| `camera` | Kamera nicht verfügbar | Die Kamera-Entität existiert nicht oder ist nicht verfügbar. | Prüfe die Kamera-Integration in Home Assistant. Alarme funktionieren weiter; das Bild und die KI-Bewertung nicht. |
| `engine` | Vital-Engine offline | Die Vital-Engine hat `offline` gemeldet oder seit mehr als 30 Sekunden keinen Zustand gesendet. | Prüfe, ob die Engine läuft, ob sie den Broker erreicht, ob ihre ID zu „ID der Vital-Engine" passt und ob ihr Präfix noch `checkbaby/engine` ist. |
| `vital_sensor` | Radarsensor nicht verfügbar | Der Atemraten-Sensor hat keinen Zahlenwert, oder er hat sich seit mehr als 120 Sekunden nicht gemeldet. | Prüfe das Radargerät und sein WLAN. Ist das Gerät in Ordnung, meldet der Sensor vermutlich nur bei einer Änderung seines Werts: Lass ihn regelmäßig melden, und entferne Filter, die wiederholte Werte unterdrücken. |
| `notify` | ein Benachrichtigungsziel fehlt | Der Benachrichtigungsdienst eines eingerichteten Handys existiert nicht; oder es ist kein Handy eingerichtet und kein Gerät für den lokalen Alarm eingetragen oder erreichbar. | Siehe [Auf dem Handy kommt keine Benachrichtigung an](#auf-dem-handy-kommt-keine-benachrichtigung-an). |
| `local_alarm` | lokaler Alarm nicht erreichbar | Eine unter „Lokaler Alarm" gewählte Entität fehlt oder ist in Home Assistant `unavailable` (nicht verfügbar), zum Beispiel eine smarte Lampe, die am Wandschalter aus ist. | Gib dem Gerät Strom und prüfe seine Integration. Der Zustellbericht von „Testalarm" nennt das Gerät. Eine Lampe, die als Alarm dient, muss am Wandschalter eingeschaltet bleiben. |
| `sleep_place` | kein Schlafplatz aktiv | Der Eintrag hat keinen Schlafplatz. | Füge mit „Schlafplatz hinzufügen" einen hinzu. |

Die Störungen haben zwei Grade:

- **Leicht:** `camera` und `local_alarm` immer, und `engine` und `vital_sensor`, solange der Schalter „Atembewegungs-Alarm" aus ist. Sie stehen in der Liste, der Binärsensor „Störung der Überwachung" ist an, und die Alarmstufe zeigt „Hinweis"; es wird aber keine Benachrichtigung gesendet, und der Zustand ändert sich nicht.
- **Ernst:** alle anderen, und `engine` und `vital_sensor`, sobald der Schalter „Atembewegungs-Alarm" an ist. Bei eingeschalteter Überwachung lösen sie die Warnung „Die Überwachung von (Name) ist gestört" aus und nach fünf Minuten einen kritischen Alarm. Bei `mqtt` (wenn eine Frigate-Kamera genutzt wird), `frigate`, `audio_level`, `cry_sensor` oder `sleep_place` zeigt außerdem der Zustand „Unbekannt".

Falls du einen Ausfall-Summer („Dead-Man-Summer") nutzt: Sein Lebenszeichen setzt nur aus, solange eine ernste Störung besteht. Eine leichte Störung lässt den Summer nicht ertönen.

In den ersten zwei Minuten nach einem Start ist eine Quelle, die sich einfach noch nicht gemeldet hat, keine Störung.

## Reparaturhinweise

| Hinweis | Ursache | Was tun |
|---|---|---|
| CheckBaby kann für (Name) niemanden alarmieren | Es ist weder ein Handy noch ein lokaler Alarm eingerichtet. | Öffne am Eintrag **Konfigurieren → Wer benachrichtigt wird** und kreuze ein Handy an oder wähle einen lokalen Alarm. |
| Für (Name) ist kein Schlafplatz eingerichtet | Der Eintrag hat keinen Schlafplatz, zum Beispiel weil du den einzigen gelöscht hast. | Füge am Eintrag mit „Schlafplatz hinzufügen" einen hinzu. |
| CheckBaby braucht MQTT für (Name) | Der aktive Schlafplatz nutzt eine Frigate-Kamera oder die Vital-Engine, aber die MQTT-Integration ist nicht eingerichtet. | Richte MQTT ein. CheckBaby bemerkt das binnen Sekunden, abonniert seine Themen und entfernt den Hinweis. Bleibt der Hinweis stehen, lade den CheckBaby-Eintrag neu. |

## Auf dem Handy kommt keine Benachrichtigung an

Fang mit dem Testalarm an, denn er berichtet, wohin er gegangen ist.

### Der Testalarm kommt nicht an

1. **Drücke „Testalarm"** auf der Geräteseite (die Taste steht unter „Diagnose"). Er funktioniert auch bei ausgeschalteter Überwachung.
2. **Lies den Zustellbericht.** Öffne die Benachrichtigungen von Home Assistant (die Glocke in der Seitenleiste). Neben dem Alarm selbst steht dort ein zweiter Eintrag, der sagt, wohin der Alarm gegangen ist:

   | Im Bericht steht | Was tun |
   |---|---|
   | „Es ist kein Handy gewählt, deshalb wurde kein Push gesendet." | Öffne am CheckBaby-Eintrag **Konfigurieren → Wer benachrichtigt wird** und kreuze das Handy unter „Handys" an. |
   | „NICHT gesendet an: notify.…" | Home Assistant hat diesen Benachrichtigungsdienst nicht mehr, oder der Dienst hat einen Fehler gemeldet. Das passiert zum Beispiel, nachdem ein Handy umbenannt oder die App neu installiert wurde. Öffne **Konfigurieren → Wer benachrichtigt wird**: Ein Ziel, das es nicht mehr gibt, steht weiter in der Liste, mit einem „?" hinter dem Namen. Entferne dort das Häkchen und kreuze das Handy unter seinem jetzigen Namen an. |
   | „Gesendet an: notify.…" | Home Assistant hat die Nachricht übergeben. Erscheint auf dem Handy nichts, liegt der Grund am Handy oder auf dem Weg dorthin; weiter bei 4. |
   | „Lokaler Alarm NICHT erreichbar: …" | Siehe `local_alarm` in der Tabelle oben. |

3. **Das Handy steht nicht in der Liste unter „Handys"?** Öffne auf diesem Handy die Home-Assistant-App und melde dich an deinem Home Assistant an. Danach erscheint das Handy mit seinem Gerätenamen in der Liste. Laut der Dokumentation der App kann ein Neustart von Home Assistant nötig sein, bevor ein neues Handy auftaucht.
4. **Im Bericht steht „Gesendet", aber auf dem Handy erscheint nichts:**
   - Prüfe in den Einstellungen des Handys, ob die Home-Assistant-App Mitteilungen senden darf.
   - Erlaube unter iOS zusätzlich kritische Hinweise, siehe [Ein kritischer Alarm ertönt nicht](#ein-kritischer-alarm-ertönt-nicht).
   - Prüfe unter Android „Nicht stören" und die Akku-Optimierung: Erlaube der App, „Nicht stören" zu umgehen, und nimm sie von der Akku-Optimierung aus, damit das Handy sie nicht schlafen legt.
   - Prüfe die Verbindung. Eine Push-Nachricht braucht normalerweise das Internet, zu Hause und am Handy.
5. **Sieh ins Protokoll.** Schalte das Debug-Protokoll ein: **Einstellungen → Geräte & Dienste → CheckBaby**, dann im Menü des Eintrags **Debug-Protokollierung aktivieren**. Oder trage das in `configuration.yaml` ein und starte neu:

   ```yaml
   logger:
     logs:
       custom_components.checkbaby: debug
   ```

   Drücke noch einmal „Testalarm" und sieh dir das vollständige Protokoll unter **Einstellungen → System → Protokolle** an. Hast du das Menü benutzt, bietet Home Assistant das Protokoll zum Herunterladen an, sobald du die Debug-Protokollierung wieder ausschaltest. Es enthält Zeilen wie `Alert test (critical, first) goes to ['mobile_app_annas_iphone']`, oder `goes to no phone`, wenn keines gewählt ist, und `Local alarm on: [...]`, wenn der lokale Alarm geschaltet wird. Die Zeilen sind englisch. Ein Benachrichtigungsdienst, der gescheitert ist, steht mit seinem Fehler im Protokoll.

### Der Testalarm kommt an, ein echter Alarm aber nicht

Dann ist der Weg zum Handy in Ordnung, und der Grund liegt in den Regeln.

1. **Ist die Überwachung an und der Privatmodus aus?** Solange die Überwachung aus oder der Privatmodus an ist, melden sich nur Rauch/CO und der Testalarm.
2. **Wer hat Dienst?** Eine Warnung geht zuerst nur an das Handy, das unter „Hat Dienst" gewählt ist, und nach drei Minuten an alle.
3. **Ist das Handy nur unter „Handys der Babysitter" angekreuzt?** Diese Handys bekommen Alarme nur, solange der Modus auf „Babysitter" steht.
4. **Läuft eine Ruhezeit?** Nach „5 min Ruhe" werden Warnungen zurückgehalten.
5. **War es nur ein Hinweis?** Hinweise (zum Beispiel lose Gegenstände im Bett, ein etwas zu warmer Raum, kein Internet) werden nie gesendet. Sie stehen in den Sensoren „Alarmstufe" und „Alarmgrund".
6. **Galt jemand als beim Kind?** Solange der Türkontakt offen ist oder die Kamera eine Person sieht und du diese Option eingeschaltet hast, ist der Zustand „Betreut", und kindbezogene Alarme pausieren. Steht der Zustand auf „Betreut", obwohl niemand im Raum ist, erkennt Frigate vermutlich das Kind als Person: Schalte die Option aus.
7. **Ist dieselbe Warnung gerade erst zu Ende gegangen?** Eine Warnung, die auf den Handys war und innerhalb von zwei Minuten wiederkommt, wird nicht erneut gesendet.

Kommt die Benachrichtigung ohne Bild an: Der Schlafplatz braucht eine Kamera-Entität, und das Handy muss dein Home Assistant erreichen können, von unterwegs über die externe Adresse.

Tut „Gesehen" in der Benachrichtigung nichts: Der Knopf braucht eine Verbindung vom Handy zurück zu Home Assistant. Nimm stattdessen die Taste „Gesehen" im Dashboard.

## Ein kritischer Alarm ertönt nicht

Ein kritischer Alarm soll ertönen, obwohl das Handy stumm ist oder „Nicht stören" eingeschaltet hat. Das erlaubt das Handy nur, wenn die Home-Assistant-App die Berechtigung dafür hat. Das Folgende stammt aus der Dokumentation der App und nicht aus eigenem Test.

**iPhone**

- Öffne in den **Einstellungen des iPhones → Mitteilungen → Home Assistant** und schalte **Kritische Hinweise** ein. iOS fragt nach dieser Berechtigung, wenn zum ersten Mal ein kritischer Alarm ankommt; hast du damals abgelehnt, schalte sie hier ein.
- Kritische Hinweise haben eine eigene Lautstärke. CheckBaby sendet sie in voller Lautstärke.

**Android**

- CheckBaby sendet kritische Alarme über den Kanal `alarm_stream`, der mit der Wecker-Lautstärke abgespielt wird. Prüfe, dass die **Wecker-Lautstärke** nicht auf null steht.
- Erlaube der Home-Assistant-App, **„Nicht stören" zu umgehen** (in den Einstellungen des Handys der Zugriff auf „Nicht stören"), und nimm die App von der **Akku-Optimierung** aus.
- Warnungen nutzen einen eigenen Kanal namens „CheckBaby". Ton und Wichtigkeit lassen sich in den Benachrichtigungseinstellungen der App ändern; sorge dafür, dass er nicht stummgeschaltet ist.

Wiederhole dann den Test: Handy stumm, „Nicht stören" an, „Testalarm" drücken.

Bleibt es weiter stumm, verlass dich auf den lokalen Alarm und dein Rückfall-Babyphone, und melde, was du gefunden hast.

## Weinen wird nicht erkannt

1. **Meldet Frigate Weinen?** Beobachte das Thema mit einem MQTT-Werkzeug, während du neben der Kamera eine Aufnahme eines weinenden Babys abspielst:

   ```bash
   mosquitto_sub -h BROKER -u BENUTZER -P PASSWORT -v -t 'frigate/+/audio/#'
   ```

   Du solltest `frigate/<kamera>/audio/dBFS` mit wechselnden Zahlen sehen und `frigate/<kamera>/audio/crying`, das auf `ON` wechselt.
2. **Gar kein `dBFS`:** Der Stream hat keinen Ton, oder die Rolle `audio` fehlt. Siehe [Frigate](frigate.md).
3. **`dBFS` kommt an, `crying` geht nie auf `ON`:** `crying` fehlt in Frigates Liste `listen` (es gehört nicht zum Standard), oder Frigates Schwellen (`min_volume`, der `threshold` des Labels) sind für deinen Raum zu streng.
4. **`crying` geht in MQTT auf `ON`, aber der Binärsensor „Weinen" bleibt aus:** Der „Name der Frigate-Kamera" im Schlafplatz oder das MQTT-Präfix unter **Konfigurieren → Weitere Geräte und Einstellungen** passt nicht, oder ein anderer Schlafplatz ist aktiv.
5. **Der Binärsensor „Weinen" geht an, aber es kommt keine Warnung:** Das Weinen muss ununterbrochen andauern. Prüfe „Weinen bis zur Warnung" und „Empfindlichkeit". Schaltet Frigate `crying` alle paar Sekunden aus und wieder ein, beginnt die Zählung jedes Mal neu; sieh dir Frigates `max_not_heard` an.
6. **Prüfe danach die Liste unter [Auf dem Handy kommt keine Benachrichtigung an](#auf-dem-handy-kommt-keine-benachrichtigung-an).**

Hat ein Schlafplatz sowohl den Namen einer Frigate-Kamera als auch einen Wein-Sensor, wird nur Frigate verwendet und der Wein-Sensor ignoriert. Um den Wein-Sensor zu nutzen, leere den Namen der Frigate-Kamera.

## Der Zustand ist „Unbekannt"

„Unbekannt" heißt: CheckBaby weiß nicht, wie es dem Kind geht. Die Gründe: Der Privatmodus ist an; eine Kernquelle ist gestört (sieh bei „Störungen der Überwachung" nach); oder CheckBaby ist gerade gestartet, und die Quellen haben sich noch nicht gemeldet.

## Die KI-Bewertung tut nichts

- **Drücke „KI-Check jetzt"** auf der Geräteseite und lies das Ergebnis in den Benachrichtigungen von Home Assistant (die Glocke in der Seitenleiste). Dort steht das Urteil der KI oder der Grund, warum kein Check lief: keine KI-Aufgabe gewählt, das Senden von Bildern nicht bestätigt, Privatmodus an, der Schlafplatz hat keine Kamera-Entität, es läuft schon ein Check, oder die KI hat keine brauchbare Antwort gegeben (mit der Fehlermeldung des Anbieters).
- Es braucht ein KI-Modell **und** das Häkchen für die Einwilligung, aus der Einrichtung oder unter **Konfigurieren → KI-Bewertung**. Die Liste unter „KI-Modell (eine „KI-Aufgabe" von Home Assistant)" ist leer, bis eine KI-Integration zu Home Assistant hinzugefügt wurde (Google Gemini, OpenRouter, Ollama); siehe [KI-Bewertung](ai-assessment.md#was-eine-ki-aufgabe-ist-und-woher-sie-kommt).
- Der Schalter „KI-Bewertung" ist standardmäßig an. Hat ihn jemand ausgeschaltet, pausieren die automatischen Bewertungen.
- Der Schlafplatz braucht eine Kamera-Entität.
- Automatische Bewertungen laufen nur, solange die Überwachung an, der Privatmodus aus und niemand beim Kind ist.
- Der Sensor „KI-Aufrufe in der letzten Stunde" zeigt, ob das Budget verbraucht ist.
- Ist „KI-Bewertung verfügbar" aus, ist der letzte Versuch gescheitert: Jede KI-Aufgabe hat nach 20 Sekunden die Zeit überschritten, einen Fehler geliefert oder eine Antwort ohne die Pflichtfelder gegeben. Das Ergebnis von „KI-Check jetzt" und das Ereignisprotokoll in der Diagnose nennen den Fehler. Manche Anbieter nehmen über AI Task möglicherweise kein Kamerabild an; das wurde noch nicht ausprobiert.

## „Atembewegung" bleibt unbekannt

Keine Vitalquelle ist brauchbar. Beim Radar: Die Entität hat keinen Zahlenwert, oder sie hat sich seit mehr als 120 Sekunden nicht gemeldet. Bei der Vital-Engine: Sie meldet `unusable` (verdeckt, zu dunkel, Kind nicht im Bild), sie ist offline, oder ihre Meldungen kommen nicht an. Siehe [Vitalquellen](vital-sources.md).

## Die Entitäts-IDs aus den Beispielen gibt es nicht

Die Beispiele verwenden ein Kind namens „baby". Deine IDs enthalten den Namen deines Kindes, und sie werden aus den Entitätsnamen in der Sprache gebildet, auf die dein Home Assistant bei der Einrichtung eingestellt war. Siehe [Entitäten und Aktionen](entities-and-actions.md#entitäts-ids-hängen-von-der-sprache-ab).

## Der lokale Alarm geht nicht aus

Der lokale Alarm folgt den Alarmen. Er wird ausgeschaltet, wenn der Alarm, der ihn eingeschaltet hat, mit „Gesehen" quittiert wird, vorbei ist oder, bei einer Warnung, mit „5 min Ruhe" geschlummert wird. Einen lokalen Alarm, der wegen eines kritischen Alarms an ist, schaltet „5 min Ruhe" nicht aus; tippe auf „Gesehen".

CheckBaby gleicht den Alarm alle zwei Sekunden und auch nach einem Neustart mit den Alarmen ab; ein Alarm, der an geblieben ist, wird also von selbst ausgeschaltet. Bleibt eine Sirene an, obwohl der Sensor „Alarmstufe" weder Warnung noch kritischen Alarm zeigt, schalte sie von Hand aus und schick die Diagnose.

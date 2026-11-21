# Fehlersuche

[English version](../en/troubleshooting.md) · [Zurück zur Übersicht](README.md)

Fang an zwei Stellen an:

- Beim Sensor **Störungen der Überwachung** am Gerät. Sein Attribut `problems` nennt, was die Ausfallüberwachung gefunden hat.
- Unter **Einstellungen → System → Reparaturen** bei den drei Reparaturhinweisen.

Bei allem Unerwarteten hilft **Diagnose herunterladen** am CheckBaby-Eintrag. Die Datei enthält das Ereignisprotokoll mit der Ursache jeder Entscheidung.

Weil CheckBaby noch nicht an echter Hardware lief, ist eine Abweichung zu Frigate, zur Home-Assistant-App oder zu einem KI-Anbieter gut möglich. Verhält sich etwas nicht wie hier beschrieben, sind das MQTT-Thema mit Nutzlast oder die Fehlermeldung aus dem Home-Assistant-Protokoll die wichtigsten Angaben für einen Fehlerbericht.

## Störungen der Überwachung

Die Namen sind die aus dem Attribut `problems`. In einer Benachrichtigung stehen sie in Worten.

| Störung | In der Benachrichtigung | Ursache | Was tun |
|---|---|---|---|
| `mqtt` | MQTT getrennt | Die MQTT-Integration ist nicht geladen oder hat den Broker verloren. | Prüfe den Broker und die MQTT-Integration. CheckBaby abonniert von selbst, sobald MQTT zurück ist. |
| `frigate` | Frigate offline | `<präfix>/available` meldet nicht `online`, oder dort kam in den zwei Minuten nach dem Start nichts an. | Prüfe, ob Frigate läuft, ob MQTT in Frigate eingeschaltet ist und ob das MQTT-Präfix in den CheckBaby-Optionen zu Frigates `topic_prefix` passt. |
| `audio_level` | kein Ton von der Kamera | Länger als 60 Sekunden kein Wert auf `<präfix>/<kamera>/audio/dBFS`. Ohne Frigate: Der Geräuschpegel-Sensor hat keinen Zahlenwert. | Prüfe, ob der Stream eine Tonspur hat, ob der Eingang die Rolle `audio` hat, ob die Audio-Erkennung für diese Kamera eingeschaltet ist und ob der „Name der Frigate-Kamera" genau so geschrieben ist wie in Frigate. |
| `microphone` | Mikrofonsignal flach | Pegel kommen an, aber der Wert hat sich 10 Minuten lang überhaupt nicht verändert. | Das Mikrofon kann tot oder in den Einstellungen der Kamera stummgeschaltet sein. Hör in den Stream hinein. Bei einem Geräuschpegel-*Sensor*, der grob rundet: aus dem Schlafplatz entfernen. |
| `cry_sensor` | Wein-Sensor nicht verfügbar | Ohne Frigate: Der Wein-Sensor ist nicht verfügbar oder unbekannt. | Prüfe das Gerät, das ihn liefert. |
| `camera` | Kamera nicht verfügbar | Die Kamera-Entität existiert nicht oder ist nicht verfügbar. | Prüfe die Kamera-Integration in Home Assistant. Alarme funktionieren weiter; das Bild und die KI-Bewertung nicht. |
| `engine` | Vital-Engine offline | Die Vital-Engine hat `offline` gemeldet oder seit mehr als 30 Sekunden keinen Zustand gesendet. | Prüfe, ob die Engine läuft, ob sie den Broker erreicht, ob ihre ID zu „ID der Vital-Engine" passt und ob ihr Präfix noch `checkbaby/engine` ist. |
| `vital_sensor` | Radarsensor nicht verfügbar | Der Atemraten-Sensor hat keinen Zahlenwert. | Prüfe das Radargerät und sein WLAN. |
| `notify` | ein Benachrichtigungsziel fehlt | Der Benachrichtigungsdienst eines eingerichteten Handys existiert nicht, oder es ist weder ein Handy noch ein lokaler Alarm eingerichtet. | Siehe [Es kommt keine Benachrichtigung an](#es-kommt-keine-benachrichtigung-an). |
| `sleep_place` | kein Schlafplatz aktiv | Der Eintrag hat keinen Schlafplatz. | Füge mit „Schlafplatz hinzufügen" einen hinzu. |

Bei eingeschalteter Überwachung löst jede davon die Warnung „Die Überwachung von (Name) ist gestört" aus und nach fünf Minuten einen kritischen Alarm. Bei `mqtt` (wenn eine Frigate-Kamera genutzt wird), `frigate`, `audio_level`, `cry_sensor` oder `sleep_place` zeigt außerdem der Zustand „Unbekannt".

In den ersten zwei Minuten nach einem Start ist eine Quelle, die sich einfach noch nicht gemeldet hat, keine Störung.

## Reparaturhinweise

| Hinweis | Ursache | Was tun |
|---|---|---|
| CheckBaby kann für (Name) niemanden alarmieren | Es ist weder ein Handy noch ein lokaler Alarm eingerichtet. | Öffne die Optionen des Eintrags und wähle mindestens eines. |
| Für (Name) ist kein Schlafplatz eingerichtet | Der Eintrag hat keinen Schlafplatz, zum Beispiel weil du den einzigen gelöscht hast. | Füge am Eintrag mit „Schlafplatz hinzufügen" einen hinzu. |
| CheckBaby braucht MQTT für (Name) | Der aktive Schlafplatz nutzt eine Frigate-Kamera oder die Vital-Engine, aber die MQTT-Integration ist nicht eingerichtet. | Richte MQTT ein und lade den CheckBaby-Eintrag neu. Der Hinweis wird nur beim Start des Eintrags geprüft und bleibt deshalb bis zum Neuladen stehen. |

## Es kommt keine Benachrichtigung an

Geh das der Reihe nach durch.

1. **Kommt der Testalarm an?** Drücke „Testalarm". Er funktioniert auch bei ausgeschalteter Überwachung. Kommt er an, ist der Weg zum Handy in Ordnung, und der Grund liegt in den Regeln (weiter bei 5).
2. **Stimmt der Benachrichtigungsdienst?** In den Optionen muss „Handys" Namen wie `mobile_app_annas_iphone` enthalten, ohne `notify.` davor. Probiere den Dienst unter **Entwicklerwerkzeuge → Aktionen** mit `notify.mobile_app_annas_iphone` aus. Ändert sich der Name des Dienstes, zum Beispiel nachdem du das Handy umbenannt hast, existiert der alte nicht mehr, und die Ausfallüberwachung meldet `notify`.
3. **Darf die Home-Assistant-App benachrichtigen?** Prüfe in den Einstellungen des Handys die Berechtigung für Mitteilungen und unter Android, dass die Akku-Optimierung die App nicht schlafen legt.
4. **Hat das Handy eine Verbindung?** Push-Nachrichten brauchen normalerweise das Internet, bei dir und beim Handy.
5. **Ist die Überwachung an und der Privatmodus aus?** Solange die Überwachung aus oder der Privatmodus an ist, melden sich nur Rauch/CO und der Testalarm.
6. **Wer hat Dienst?** Eine Warnung geht zuerst nur an das Handy, das unter „Hat Dienst" gewählt ist, und nach drei Minuten an alle.
7. **Läuft eine Ruhezeit?** Nach „5 min Ruhe" werden Warnungen zurückgehalten.
8. **War es nur ein Hinweis?** Hinweise (zum Beispiel lose Gegenstände im Bett, ein etwas zu warmer Raum, kein Internet) werden nie gesendet. Sie stehen in den Sensoren „Alarmstufe" und „Alarmgrund".
9. **Galt jemand als beim Kind?** Solange der Türkontakt offen ist oder die Kamera eine Person sieht und du diese Option eingeschaltet hast, ist der Zustand „Betreut", und kindbezogene Alarme pausieren. Steht der Zustand auf „Betreut", obwohl niemand im Raum ist, erkennt Frigate vermutlich das Kind als Person: Schalte die Option aus.
10. **Ist dieselbe Warnung gerade erst zu Ende gegangen?** Eine Warnung, die innerhalb von zwei Minuten wiederkommt, wird nicht erneut gesendet.

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
4. **`crying` geht in MQTT auf `ON`, aber der Binärsensor „Weinen" bleibt aus:** Der „Name der Frigate-Kamera" im Schlafplatz oder das MQTT-Präfix in den Optionen passt nicht, oder ein anderer Schlafplatz ist aktiv.
5. **Der Binärsensor „Weinen" geht an, aber es kommt keine Warnung:** Das Weinen muss ununterbrochen andauern. Prüfe „Weinen bis zur Warnung" und „Empfindlichkeit". Schaltet Frigate `crying` alle paar Sekunden aus und wieder ein, beginnt die Zählung jedes Mal neu; sieh dir Frigates `max_not_heard` an.
6. **Prüfe danach die Liste unter [Es kommt keine Benachrichtigung an](#es-kommt-keine-benachrichtigung-an).**

Hast du im selben Schlafplatz sowohl den Namen einer Frigate-Kamera als auch einen Wein-Sensor eingetragen, entferne eines von beiden; die zwei überschreiben sich gegenseitig.

## Der Zustand ist „Unbekannt"

„Unbekannt" heißt: CheckBaby weiß nicht, wie es dem Kind geht. Die Gründe: Der Privatmodus ist an; eine Kernquelle ist gestört (sieh bei „Störungen der Überwachung" nach); oder CheckBaby ist gerade gestartet, und die Quellen haben sich noch nicht gemeldet.

## Die KI-Bewertung tut nichts

- Der Schalter „KI-Bewertung" ist standardmäßig aus.
- Die Optionen brauchen mindestens eine KI-Aufgabe **und** das Häkchen für die Einwilligung.
- Der Schlafplatz braucht eine Kamera-Entität.
- Automatische Bewertungen laufen nur, solange die Überwachung an, der Privatmodus aus und niemand beim Kind ist.
- Der Sensor „KI-Aufrufe in der letzten Stunde" zeigt, ob das Budget verbraucht ist.
- Ist „KI-Bewertung verfügbar" aus, ist der letzte Versuch gescheitert: Jede KI-Aufgabe hat nach 20 Sekunden die Zeit überschritten, einen Fehler geliefert oder eine Antwort ohne die Pflichtfelder gegeben. Das Ereignisprotokoll in der Diagnose nennt den Fehler. Manche Anbieter nehmen über AI Task möglicherweise kein Kamerabild an; das wurde noch nicht ausprobiert.

## „Atembewegung" bleibt unbekannt

Keine Vitalquelle ist brauchbar. Beim Radar: Die Entität hat keinen Zahlenwert. Bei der Vital-Engine: Sie meldet `unusable` (verdeckt, zu dunkel, Kind nicht im Bild), sie ist offline, oder ihre Meldungen kommen nicht an. Siehe [Vitalquellen](vital-sources.md).

## Die Entitäts-IDs aus den Beispielen gibt es nicht

Die Beispiele verwenden ein Kind namens „baby". Deine IDs enthalten den Namen deines Kindes, und sie werden aus den Entitätsnamen in der Sprache gebildet, auf die dein Home Assistant bei der Einrichtung eingestellt war. Siehe [Entitäten und Aktionen](entities-and-actions.md#entitäts-ids-hängen-von-der-sprache-ab).

## Der lokale Alarm geht nicht aus

Der lokale Alarm wird ausgeschaltet, sobald keine Warnung und kein kritischer Alarm mehr unbeantwortet ist. „5 min Ruhe" bewirkt das nicht; tippe auf „Gesehen".

In dieser Version gibt es ein bekanntes Problem: Nach „5 min Ruhe" bei einer Warnung, deren lokaler Alarm schon an war, bleibt der lokale Alarm an, auch wenn die Ursache vorbei und kein Alarm mehr aktiv ist. „Gesehen" hat dann nichts zu quittieren. Schalte den Alarm von Hand aus, oder drücke „Testalarm" und danach „Gesehen"; das schaltet ihn aus.

Bleibt eine Sirene in einer anderen Lage an, schalte sie von Hand aus und schick die Diagnose.

# Frigate

[English version](../en/frigate.md) · [Zurück zur Übersicht](README.md)

Frigate hört und sieht: Es erkennt Weinen im Ton der Kamera, misst den Geräuschpegel und erkennt Bewegung. CheckBaby verarbeitet selbst weder Ton noch Bild. Es abonniert, was Frigate per MQTT veröffentlicht, und entscheidet, was das für das Kind bedeutet.

Die MQTT-Themen unten sind die aus dem Code. Sie folgen der Frigate-Dokumentation und wurden noch nicht an einem laufenden Frigate überprüft. Veröffentlicht deine Frigate-Version etwas anderes, meldet CheckBaby eine Störung der Überwachung, statt still zu bleiben. Thema und Nutzlast, die du dann siehst, sind die wichtigste Angabe für einen Fehlerbericht.

## Was CheckBaby liest

`<präfix>` ist das MQTT-Präfix von Frigate. Der Standard ist `frigate`; wenn du in Frigate `topic_prefix` geändert hast, trage denselben Wert in den CheckBaby-Optionen unter **MQTT-Präfix von Frigate** ein. `<kamera>` ist der **Name der Frigate-Kamera** des aktiven Schlafplatzes, `<zone>` dessen **Frigate-Zone des Bettes**.

| Thema | Erwartete Nutzlast | Was CheckBaby damit macht |
|---|---|---|
| `<präfix>/available` | `online`; alles andere zählt als offline | Ausfallüberwachung: Frigate läuft. |
| `<präfix>/<kamera>/audio/crying` | `ON` / `OFF` | Weinen ist zu hören. |
| `<präfix>/<kamera>/audio/scream` | `ON` / `OFF` | Schreien ist zu hören. Es zählt wie Weinen, mit kürzerer Bestätigungszeit. |
| `<präfix>/<kamera>/audio/dBFS` | eine Zahl | Geräuschpegel. Speist den Pegelsensor, den gelernten Grundpegel und „laut". Zugleich der Beleg für die Ausfallüberwachung, dass Ton ankommt. |
| `<präfix>/<kamera>/motion` | `ON` / `OFF` | Bewegung im Bild. |
| `<präfix>/<kamera>/person` | eine Anzahl | Nur wenn „Eine von der Kamera erkannte Person zählt als Betreuung" an ist: Eine Anzahl über null heißt, jemand ist beim Kind. |
| `<präfix>/<zone>/cat`, `<präfix>/<zone>/dog` | eine Anzahl | Nur wenn eine Bett-Zone gesetzt ist: Eine Anzahl über null löst die Warnung „Haustier im Bett" aus. |

Nutzlasten, die sich nicht lesen lassen (keine Zahl, wo eine Zahl erwartet wird), werden ignoriert.

CheckBaby liest **nicht**: andere Audio-Labels wie `yell` oder `speech`, `audio/rms`, `frigate/events`, `frigate/reviews`, Schnappschüsse oder Clips. Das Bild in einer Benachrichtigung kommt von der Kamera-Entität in Home Assistant, nicht von Frigate.

Abonniert wird nur der aktive Schlafplatz. Wenn du den Schlafplatz wechselst, beendet CheckBaby die alten Abonnements und abonniert die neue Kamera.

## Wofür Frigate eingerichtet sein muss

Ein Beispiel liegt in [`docs/examples/frigate-camera.yaml`](../examples/frigate-camera.yaml). Worauf es ankommt:

1. **MQTT ist in Frigate eingeschaltet** und nutzt denselben Broker wie Home Assistant.
2. **Der Kamerastream enthält Ton**, und ein Eingang der Kamera hat die Rolle `audio`. Viele günstige Kameras liefern RTSP ohne Ton; siehe [Hardware](hardware.md).
3. **Die Audio-Erkennung ist für die Kamera eingeschaltet**, und **`listen` enthält `crying` und `scream`**. Laut Frigate-Dokumentation ist die Standardliste `bark`, `fire_alarm`, `scream`, `speech`, `yell`. `crying` steht nicht darin; mit den Standardwerten meldet Frigate also nie Weinen. `yell` kannst du für eigene Zwecke ergänzen; CheckBaby ignoriert es.
4. **Die Bewegungserkennung läuft** für die Kamera, damit `<kamera>/motion` veröffentlicht wird.
5. Optional, für die Haustier-Warnung: Frigate verfolgt `cat` und `dog`, und eine Zone deckt das Bett ab. Trage den Namen der Zone im Schlafplatz ein.
6. Optional, für „Person zählt als Betreuung": Frigate verfolgt `person`. Lass die Option aus, wenn Frigate das Kind selbst als Person erkennt. Sonst würde das Kind als seine eigene Betreuung zählen, und die Alarme würden pausieren.

Frigates eigene Schwellen (`min_volume`, der `threshold` je Label, `max_not_heard`) entscheiden, wann `crying` auf `ON` und wieder auf `OFF` geht. CheckBaby legt danach seine eigenen Zeiten darüber, siehe [So funktioniert es](how-it-works.md).

Aufzeichnung und Aufbewahrung bleiben bei Frigate. Für eine Kamera in deinem eigenen Schlafzimmer überlege, nichts oder nur kurz aufzuzeichnen; siehe [Sicherheit und Datenschutz](safety-and-privacy.md).

## Was die Ausfallüberwachung von Frigate erwartet

Solange ein Schlafplatz eine Frigate-Kamera nutzt, werden diese Quellen überwacht. Jede, die ausfällt, erscheint mit ihrem Namen im Sensor **Störungen der Überwachung**:

| Störung | Bedeutung |
|---|---|
| `mqtt` | Die MQTT-Integration ist nicht geladen oder nicht mit dem Broker verbunden. |
| `frigate` | `<präfix>/available` meldet nicht `online`, oder dort kam in den zwei Minuten nach dem Start nichts an. |
| `audio_level` | Auf `<kamera>/audio/dBFS` kam länger als 60 Sekunden kein Geräuschpegel an. |
| `microphone` | Pegel kommen an, aber der Wert hat sich zehn Minuten lang überhaupt nicht verändert. Das deutet auf ein totes Mikrofon oder einen stummgeschalteten Stream hin. |

`mqtt`, `frigate` und `audio_level` sind Kernquellen. Solange eine davon gestört ist, weiß CheckBaby nicht, wie es dem Kind geht, und der Zustand zeigt „Unbekannt" statt „Schläft".

## Ohne Frigate

Ein Schlafplatz kann stattdessen gewöhnliche Home-Assistant-Entitäten nutzen. Lass **Name der Frigate-Kamera** leer und fülle aus:

| Feld | Entität | Hinweise |
|---|---|---|
| Wein-Sensor | ein Binärsensor | Pflicht. An, solange das Kind weint, zum Beispiel die Wein-Erkennung der Kamera selbst. |
| Bewegungssensor | ein Binärsensor | Optional. An, solange sich etwas bewegt. |
| Geräuschpegel-Sensor | ein Sensor mit Zahlenwert | Optional. Er wird mit dem gelernten Grundpegel plus einem Abstand in dB verglichen, sollte also ein Pegel in dB sein. |

CheckBaby liest diese Entitäten alle zwei Sekunden und sofort, wenn sich der Wein- oder Bewegungssensor ändert. Die Ausfallüberwachung meldet `cry_sensor`, wenn der Wein-Sensor nicht verfügbar ist, und `audio_level`, wenn der Pegelsensor keinen Zahlenwert hat; in beiden Fällen wird der Zustand „Unbekannt".

Der Geräuschpegel-Sensor muss sich bewegen. Bleibt sein Wert zehn Minuten lang exakt gleich, geht CheckBaby von einem toten Mikrofon aus und meldet `microphone`. Ein Sensor, der grob rundet oder selten aktualisiert, löst das in einem ruhigen Raum aus; lass das Feld dann leer.

Ohne Frigate gibt es kein Schrei-Signal, keine Haustier-Warnung und kein „Person zählt als Betreuung".

**Kombiniere die beiden Wege nicht.** Hat ein Schlafplatz sowohl den Namen einer Frigate-Kamera als auch einen Wein- oder Bewegungssensor, schreiben beide dasselbe Signal, und die Entität überschreibt alle zwei Sekunden den Wert von Frigate. Der Geräuschpegel-Sensor wird ignoriert, sobald der Name einer Frigate-Kamera eingetragen ist.

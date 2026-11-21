# Hardware

[English version](../en/hardware.md) · [Zurück zur Übersicht](README.md)

Diese Seite sammelt, was die Recherche des Projekts ergeben hat. **Keines der hier genannten Geräte wurde bisher mit CheckBaby getestet.** Die Angaben zu Kameras stammen von Herstellerseiten, aus der Frigate-Dokumentation und aus Forenberichten. Nimm die Tabellen als Ausgangspunkt für deine eigene Prüfung, nicht als Liste geprüfter Hardware; eine geprüfte Liste folgt, sobald es sie gibt.

## Was die Kamera können muss

- **RTSP und Ton im selben Stream.** Frigate erkennt Weinen aus dem Ton der Kamera. Viele günstige Kameras bieten kein RTSP mehr oder RTSP ohne Ton.
- **Ein brauchbares Infrarot-Nachtbild** aus etwa einem Meter Abstand, ohne dass das Bett überstrahlt.
- **Eine stabile Verbindung über Wochen.** Ein Babyphone, das einmal pro Nacht aussetzt, nützt wenig.

## Kamera-Kandidaten

Alle Kandidaten sind günstige WLAN-Innenkameras mit Netzteil. Nicht jedes Modell einer Marke kann RTSP; entscheidend ist das genaue Modell.

| Kandidat | RTSP und Ton | Gegensprechen | Hinweise |
|---|---|---|---|
| UniFi G3 Instant | Über die UniFi-Protect-Konsole, nicht direkt von der Kamera; in go2rtc als `rtspx://` | Nur in der Protect-App | 1080p, 111° Weitwinkel, Infrarot bis 6 m. Die Konsole wird Teil der Alarmkette. CheckBaby überwacht die Konsole nicht selbst; fällt sie aus, siehst du das als fehlenden Ton (`audio_level`) oder als nicht verfügbare Kamera. |
| Reolink E1 Pro / E1 Zoom (Schwenkkopf) | Direkt, Ton als AAC | Über go2rtc, modellabhängig | Siehe die Kauffalle unten. |
| TP-Link Tapo C200 / C210 / C120 | Direkt, nach Aktivierung in der App | Über go2rtc (`tapo://`), je nach Firmware | Günstig. Die App drängt zur Cloud, das lässt sich ignorieren. |
| Eufy-Innenkamera mit Schwenkkopf | Unklar | Unklar | Keine belastbaren Berichte mit Frigate gefunden. Nicht ohne eigenen Test kaufen. |

### Die Kauffalle: die einfache Reolink E1

**Die einfache Reolink E1 (ohne „Pro" oder „Zoom") kann RTSP und ONVIF nicht direkt.** Sie funktioniert nur über einen Reolink-Hub oder -NVR. E1 Pro und E1 Zoom können RTSP. Die Namen unterscheiden sich um ein Wort, und die Verpackungen sehen sich ähnlich. Prüfe deshalb das genaue Modell, bevor du bestellst.

### So wählst du aus

Vergleiche, wenn möglich, zwei Kameras direkt nebeneinander in vier Punkten:

1. Ist Ton im Stream, und kann Frigate ihn auswerten?
2. Wie sieht das Infrarotbild aus etwa einem Meter aus: überstrahlt, scharf, verrauscht?
3. Wie groß ist die Verzögerung von Bild und Ton?
4. Läuft sie 14 Tage ohne Aussetzer?

### Schwenkkameras

Ein Schwenkkopf ist praktisch bei mehreren Schlafplätzen. Nach jedem Schwenk passen aber die Bett-Zone in Frigate und der Bildausschnitt der Vital-Engine nicht mehr zum Bild. Nutze einen festen Preset „Bett" und kehre dorthin zurück. CheckBaby erkennt eine verstellte Kamera nicht von selbst; nur die KI-Bewertung kann bemerken, dass das Bild kein Bett mehr zeigt („Kamerablick verdeckt"), und nur, wenn du sie nutzt.

## Stückliste

Pflicht ist nur die Kamera. Alles andere bringt eine Funktion dazu.

| Teil | Wofür CheckBaby es nutzt |
|---|---|
| Innenkamera mit RTSP und Ton | Bild, Ton, Frigate-Erkennung |
| Türkontakt | „Jemand ist beim Kind": pausiert die kindbezogenen Alarme, solange die Tür offen ist |
| Sirene, oder Lampe oder Zwischenstecker, im Elternschlafzimmer | Lokaler Alarm, der ohne Internet funktioniert |
| Temperatur- und Feuchtesensor | Anzeige des Raumklimas, Alarm für den Temperaturbereich, Schlafsack-Empfehlung |
| Seeed MR60BHA2 | Lokale Radarquelle für den Atembewegungs-Hinweis, siehe [Vitalquellen](vital-sources.md) |
| Aqara FP2 | Lokaler Präsenzsensor für das Bett; seine Vitaldaten nur über die Cloud |
| ESP32 mit Summer | Ausfall-Summer („Dead-Man-Summer"): Er ertönt, wenn Home Assistant verstummt, siehe [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml) |
| Rauch- und CO-Melder, die Home Assistant auslesen kann | Werden als kritischer Alarm durchgereicht |
| Ein Sensor, der anzeigt, ob das Internet erreichbar ist | Lässt den lokalen Alarm sofort auslösen, solange das Internet ausgefallen ist |
| USV für Server, Switch und Router (optional) | Überbrückt kurze Stromausfälle |

Ohne lokalen Alarm hängt jeder Alarm an der Push-Nachricht, und die läuft normalerweise über die Server von Apple oder Google. Fällt deine Internetverbindung aus, ist eine Sirene oder Lampe in deinem Schlafzimmer der Kanal, der noch funktioniert.

## Montage und Kabelsicherheit

**Kabel sind die eigentliche Gefahr am Kinderbett.** Ein Kind kann ein Kabel ins Bett ziehen und sich darin verfangen.

- Halte jedes Kabel, jedes Netzteil und jedes Gerät **mindestens einen Meter vom Bett entfernt und außer Reichweite des Kindes**. Denk daran, dass die Reichweite wächst: Ein Kind, das heute nicht stehen kann, steht in ein paar Monaten.
- Führe Kabel in einem Kabelkanal an der Wand entlang, nicht lose und nicht am Bett entlang.
- Befestige nichts am Bett selbst, und lege nichts ins Bett. Das gilt auch für Sensoren.
- Montiere die Kamera so, dass sie nicht ins Bett fallen kann: an Wand oder Decke geschraubt, nicht auf einer Regalkante über dem Bett.

Für das Bild:

- Montiere die Kamera **möglichst senkrecht über dem Bett**. Ein flacher Winkel schwächt die KI-Bewertung und die Vital-Engine.
- Prüfe das Nachtbild bei dunklem Raum. Überstrahlt das Infrarotlicht die Matratze, vergrößere den Abstand oder ändere den Winkel.
- Hängt die Kamera in den ersten Monaten in deinem eigenen Schlafzimmer, denk an den Privatmodus und daran, was Frigate aufzeichnet; siehe [Sicherheit und Datenschutz](safety-and-privacy.md).

Für den lokalen Alarm:

- Stelle Sirene oder Lampe **dorthin, wo du schläfst, nie ins Kinderzimmer**.

Für Radarsensoren:

- Alle erhältlichen Module sind für Erwachsene bei bis zu 1,5 m ausgelegt. Forschung an Frühgeborenen arbeitete mit eigener Auswertung der Rohdaten aus etwa 45 cm Abstand. Welcher Abstand und Winkel bei einem Säugling mit einem fertigen Modul funktioniert, ist nicht bekannt und muss gemessen werden. Es gelten dieselben Regeln für Kabel.

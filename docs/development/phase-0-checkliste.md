# Phase 0: Checkliste für die Prüfungen am echten System

Diese vier Prüfungen brauchen dein laufendes Frigate, die Kamera und die Sensoren. Die Ergebnisse entscheiden über offene Punkte im [Masterplan](../MASTERPLAN.md) (Abschnitt 9). Trage sie bitte als kurze Notiz je Prüfung unter `docs/development/spikes/` ein oder schick sie formlos.

Die Konfigurationsbeispiele stammen aus Dokumentation und Forenberichten und sind noch nicht an einem echten System geprüft. Wenn etwas nicht wie beschrieben funktioniert, ist genau das ein Ergebnis: bitte Fehlermeldung und Version notieren.

## 0. Vorab

- [ ] Frigate-Version, Home-Assistant-Version, MQTT-Broker notieren.
- [ ] Grafikeinheit des Frigate-Rechners: Typ und Grafikspeicher (bei Nvidia `nvidia-smi`).
- [ ] UniFi: Läuft eine Protect-Konsole? Welches Kameramodell genau?
- [ ] Bestellen: Seeed MR60BHA2 (Kit mit ESP32-C6), Aqara FP2, Türkontakt, Temperatur-/Feuchtesensor.

## 1. Frigate: Ton und Wein-Erkennung

Ziel: Kommt Ton an, erkennt Frigate Weinen, wie schnell, und wie sehen die MQTT-Nachrichten aus?

1. Kamera in Frigate mit Ton einrichten (Schema laut Frigate-Doku):

   ```yaml
   audio:
     enabled: true
     listen:
       - crying
       - scream
       - yell
   cameras:
     babyzimmer:
       ffmpeg:
         inputs:
           - path: rtsp://127.0.0.1:8554/babyzimmer
             roles:
               - audio
               - detect
               - record
   ```

2. MQTT mitschneiden:

   ```bash
   mosquitto_sub -h BROKER -u BENUTZER -P PASSWORT -v -t 'frigate/babyzimmer/audio/#' -t 'frigate/events' -t 'frigate/reviews'
   ```

3. Eine Aufnahme von Babyweinen vom Handy in realistischer Lautstärke neben der Kamera abspielen.

Notieren:

- [ ] Welche Themen und Werte erscheinen (zwei, drei Beispielzeilen genügen)?
- [ ] Sekunden vom Beginn des Weinens bis `crying` auf `ON` geht.
- [ ] Pegel (`dBFS`) bei Stille, bei Weinen, bei laufendem weißen Rauschen.
- [ ] Wie oft pro Sekunde kommen Pegelwerte?
- [ ] Wird das Weinen auch aus 2 bis 3 m Abstand und bei geschlossener Tür erkannt?

## 2. KI-Bewertung über AI Task

Ziel: Nimmt `ai_task` ein Kamerabild an, liefert es strukturierte Antworten, und taugt das Nachtbild?

Voraussetzung: eine AI-Task-Entität (Google Gemini oder OpenRouter, zusätzlich ein lokales Modell, falls die Grafikeinheit reicht).

In Home Assistant unter Entwicklerwerkzeuge → Aktionen:

```yaml
action: ai_task.generate_data
data:
  task_name: CheckBaby Test
  entity_id: ai_task.DEINE_ENTITAET
  instructions: >-
    The image shows a baby cot from above. Report the position of the baby
    (or doll), whether the face is visible and uncovered, and any loose
    objects in the cot.
  attachments:
    - media_content_id: media-source://camera/camera.babyzimmer
      media_content_type: image/jpeg
  structure:
    position:
      description: Body position
      required: true
      selector:
        select:
          options: [supine, prone, side, sitting, standing, not_visible]
    face_visible:
      description: Face visible and uncovered
      required: true
      selector:
        boolean:
    hazards:
      description: Loose objects in the cot, comma separated, empty if none
      selector:
        text:
response_variable: result
```

Mit einer Puppe durchspielen: Rückenlage, Bauchlage, Tuch über dem Gesicht, Kuscheltier im Bett, leeres Bett. Jeweils bei Tageslicht und im Infrarot-Nachtbild.

Notieren:

- [ ] Funktioniert der Aufruf mit Bildanhang? Falls nicht: Fehlermeldung.
- [ ] Trefferquote je Szene, getrennt nach Tag und Nacht, je Modell.
- [ ] Antwortzeit je Modell.
- [ ] Nimmt der Anbieter auch mehrere Bilder oder einen kurzen Clip an?

## 3. Kamera, go2rtc und Ton auf Lautsprecher

Ziel: Welche Kamera taugt, und lässt sich der Ton auf einen Lautsprecher legen?

- [ ] go2rtc-Oberfläche (`http://FRIGATE:1984`) öffnen: Welche Video- und Tonformate liefert die Kamera?
- [ ] Verzögerung messen: vor der Kamera klatschen, Zeit bis Bild und Ton im Dashboard ankommen.
- [ ] Infrarotbild aus etwa 1 m Abstand: überstrahlt, scharf, rauscht?
- [ ] Funktioniert Gegensprechen über die Frigate-Oberfläche?
- [ ] Lässt sich der Ton-Stream auf einem Lautsprecher im Schlafzimmer abspielen (Mediaplayer → Medium abspielen)? Mit welcher Verzögerung?
- [ ] Falls zwei Kameras da sind: beide 14 Tage laufen lassen, Aussetzer zählen.

## 4. Radar: Vortest an Erwachsenen

Ziel: Was liefern MR60BHA2 und FP2 wirklich?

- [ ] MR60BHA2 in Home Assistant aufnehmen (ESPHome), 0,5 bis 1 m über einer liegenden Person. Atemrate und Puls mit Smartwatch oder Pulsoximeter vergleichen.
- [ ] Wie schnell reagiert der Wert, wenn man 20 s die Luft anhält? Was meldet der Sensor dann?
- [ ] Wie verhält er sich bei leerem Bett und bei Bewegung?
- [ ] FP2: Präsenz-Zone „Bett" lokal über HomeKit einbinden. Vitaldaten über das SleepRadar-Add-on: Verzögerung, Verhalten ohne Internet.
- [ ] Beide Sensoren gleichzeitig am selben Bett: ändern sich die Werte?

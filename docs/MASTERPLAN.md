# HACheckBaby – Masterplan

Stand: 21.11.2026 (vierte Fassung: mit Umsetzungsstand) · Status: Die Software ist geschrieben und automatisch getestet, aber noch nie an echter Hardware gelaufen. Was fertig ist und was fehlt, steht in [Abschnitt 11](#11-umsetzungsstand); die Prüfungen am echten System in der [Checkliste](development/phase-0-checkliste.md)

Ein lokales, smartes Babyphone für Home Assistant, das auf Frigate aufsetzt und über HACS installiert wird. Es soll alles können, was ein klassisches Babyphone kann, und darüber hinaus die Lage im Bett bewerten: nicht nur „es bewegt sich etwas" oder „es ist laut", sondern „geht es dem Kind gut?".

---

## 1. Kurzfassung

- **Was wir bauen:** eine HACS-Integration (Domain `checkbaby`, Anzeigename „CheckBaby – Smart Baby Monitor"), die Signale aus Frigate (Weinen, Lautstärke, Bewegung, Zonen), optionalen Sensoren (mmWave-Radar, Raumklima, Türkontakt) und einem KI-Bewertungsmodell zu einem Kind-Zustand verdichtet und daraus dreistufige Benachrichtigungen ableitet (Info → Warnung → kritischer Push).
- **Drei Schichten, klar getrennt:**
  1. **Deterministische Erkennung** (Frigate + Schwellwerte + Timer). Sie trägt alle Alarme und funktioniert ohne KI und ohne Internet.
  2. **Vital-Engine** (eigener Prozess): Atem-Mikrobewegung aus dem Videobild, optional Radar. Startet im Schattenmodus, alarmiert erst nach Validierung.
  3. **KI-Lagebewertung** (multimodales Modell, Cloud als Opt-in oder lokal): Lage, Gesicht frei, Gefahren im Bett, wach/schlafend, Klartext-Begründung.
- **Wichtigste Designregel:** Die KI darf Alarme anreichern und (mit Bestätigung) hochstufen, aber niemals einen deterministischen Warn- oder Kritisch-Alarm unterdrücken.
- **Wichtigste Zuverlässigkeitsregel:** Ein Babyphone, das still ausfällt, ist schlimmer als keins. Der Watchdog („Überwachung ausgefallen") gehört deshalb in das MVP, nicht in eine spätere Version.
- **Zwei Punkte aus der Anforderung, die der Plan anders löst als ursprünglich gedacht** (Begründung in Abschnitt 2 und 6):
  - Atemstillstand lässt sich nicht mit einem Entscheidungsmodell wie Gemini erkennen. Dafür braucht es Signalverarbeitung bzw. Radar. Das Modell bekommt die Aufgaben, die es wirklich gut kann.
  - „Ohne Internet" und „Gemini" schließen sich aus. **Entschieden:** Alles wird lokal verarbeitet, nur die KI-Bewertung darf als Opt-in in die Cloud (Gemini, OpenRouter). Wer strikt lokal bleiben will, nutzt ein lokales Modell oder lässt die KI weg; die Alarme funktionieren trotzdem.
- **Zeitrahmen:** Geburt im Februar 2027. Alles Alarmrelevante muss vorher fertig und getestet sein (Zeitplan in Abschnitt 7).

---

## 2. Ehrliche Einordnung: was das System leisten kann

Dieser Abschnitt steht absichtlich vorne, weil er Architektur und Wortwahl bestimmt.

**Plötzlicher Kindstod (SIDS).** Kein Überwachungsgerät hat bisher nachgewiesen, dass es SIDS verhindert. Die American Academy of Pediatrics rät in ihrer Empfehlung von 2022 ausdrücklich davon ab, Heimmonitore als Strategie zur SIDS-Risikosenkung einzusetzen. Die Nutzung ist nicht schädlich, aber sie ersetzt die belegten Maßnahmen nicht: Rückenlage, feste flache Unterlage, eigenes Bett im Elternzimmer, keine losen Decken/Kissen/Kuscheltiere, nicht überwärmen, rauchfrei.

Daraus folgt für uns:

- Wir bauen ein **Aufmerksamkeits- und Komfortsystem**, kein Medizinprodukt. Es darf Eltern nie in falscher Sicherheit wiegen.
- Der größte reale Sicherheitsbeitrag liegt nicht im Atemalarm, sondern im **Safe-Sleep-Check**: Das System erkennt Bauchlage, verdecktes Gesicht, lose Gegenstände im Bett und zu warme Räume. Das sind genau die Risikofaktoren, bei denen Eingreifen nachweislich hilft, und genau die Aufgaben, die ein Bildmodell beherrscht.
- Der Atem-Hinweis kommt als zusätzliche Schicht, mit offen kommunizierter Fehlalarm- und Ausfallquote.
- **Wortwahl im öffentlichen Repo:** „Atembewegungs-Hinweis", nicht „Atemüberwachung" oder „SIDS-Schutz". Software, die mit dem Zweck beworben wird, physiologische Vorgänge zu überwachen oder Krankheiten zu verhindern, kann unter die EU-Medizinprodukteverordnung fallen. Für ein Hobbyprojekt ist das mit sauberer Zweckbestimmung und Disclaimer vermeidbar, sollte vor v1.0 aber einmal rechtlich geprüft werden.
- Empfehlung an alle Nutzer (und an uns selbst): ein einfaches Audio-Babyphone als Rückfallebene behalten. Das war auch der deutlichste Konsens im Reddit-Thread.

**Warum ein Entscheidungsmodell keinen Atemstillstand erkennt.** Atmung ist eine periodische Bewegung von Bruchteilen eines Pixels bei 0,3–1 Hz. Ein Sprach-/Bildmodell sieht einzelne Standbilder, braucht Sekunden für eine Antwort, antwortet nicht deterministisch und kann überzeugend falsch liegen. Für Atmung braucht es eine kontinuierliche Zeitreihe mit 5–10 Bildern pro Sekunde oder einen Radarsensor. Die Rollen sind deshalb getrennt. Weil die Modelle besser werden, legen wir von Anfang an einen Vergleichssatz eigener Szenen an (Abschnitt 8). Damit lässt sich jedes neue Modell messen, auch an der Frage „atmet das Kind?", und die Rollenverteilung anhand von Zahlen neu entscheiden statt nach Gefühl.

| Aufgabe | Richtiges Werkzeug |
|---|---|
| Weinen, Schreien, Husten | Frigate-Audioerkennung + Dauer/Lautstärke-Logik |
| Bewegung, wach/unruhig, Kind steht | Frigate-Bewegung, Zonen, ggf. Frigate-Zustandsklassifikation |
| Atem-Mikrobewegung | Signalverarbeitung auf dem Videostream, mmWave-Radar |
| Lage, Gesicht frei, Gefahren im Bett, „sieht das normal aus?" | Multimodales KI-Modell |
| Klartext-Zusammenfassung, Nachtbericht | KI-Modell |

---

## 3. Recherche: was es schon gibt

**Ergebnis:** Eine HACS-Integration, die Frigate-Signale, Vital-Hinweise und KI-Bewertung zu einem Babyphone zusammenführt, existiert nicht. Es gibt Einzelbausteine:

| Kategorie | Beispiele | Was fehlt |
|---|---|---|
| Hersteller-Integrationen | Nanit, CuboAI, Philips Avent (Proxy), Owlet | Cloud-/Herstellerbindung, keine eigene Logik |
| Protokoll-Tools | Baby Buddy, Baby Tracker | Nur manuelles Tracking (Flasche, Windel, Schlaf) |
| DIY-Anleitungen | HA-Blog 2017 (`ffmpeg_noise`), techdout 2019, diverse Frigate-Guides | YAML-Bastelei, reine Lautstärkeschwelle, kein Watchdog, keine Eskalation |
| Atem-Forschungsprojekte | CribSense (Raspberry Pi, Video Magnification), respmon | Prototypen, nicht in HA integriert, teils zu rechenintensiv |
| Radar | Seeed MR60BHA2 (60 GHz, ESPHome, liefert Atem-/Herzrate) | Für Erwachsene bei 1,5 m ausgelegt, keine Validierung an Säuglingen |

**Was Frigate bereits liefert** (Details in Phase 0 am echten System verifizieren):

- Audioerkennung mit Labels wie `crying`, `scream`, `yell`, `speech`; nur `bark, fire_alarm, scream, speech, yell` sind Standard, `crying` muss explizit in `listen` aufgenommen werden. Schwelle je Label (Standard 0,8), `min_volume`, `max_not_heard`.
- MQTT pro Kamera: `audio/<label>` (ON/OFF), `audio/rms`, `audio/dBFS`, `motion`, dazu `frigate/events` und `frigate/reviews`.
- GenAI-Review-Zusammenfassungen (ab 0.17) mit Ollama oder Gemini. Für unsere Zwecke zu grob (Fokus: verdächtig/gefährlich im Sicherheitskontext), aber ein Beleg, dass der Ansatz trägt.
- go2rtc-Restream: ein Kamerazugriff, mehrere Abnehmer (Frigate, Live-Ansicht, unsere Vital-Engine).

**Lehren aus dem Reddit-Thread und den Anleitungen:**

1. Zuverlässigkeit schlägt Features. „Zum Laufen bringen" und „ein Jahr ohne Ausfall laufen" sind zwei verschiedene Dinge.
2. Reine Lautstärkeschwellen erzeugen zu viele Fehlalarme. Gewünscht: Dauer und Trend statt Ein/Aus (zehn Sekunden Quengeln ist kein Alarm).
3. Kritische Push-Nachrichten, die „Nicht stören" durchbrechen, sind der entscheidende Vorteil gegenüber normalem Push.
4. Schnappschuss oder Clip gehört in die Benachrichtigung, damit man ohne App-Start entscheiden kann.
5. „Wer hat Dienst?" (Mama/Papa/beide) als Umschalter, Türsensor für größere Kinder, Lampe im Elternschlafzimmer als stiller Kanal.
6. Kamerafalle: Viele günstige Kameras haben kein RTSP mehr oder RTSP ohne Ton. Eine geprüfte Hardwareliste ist Teil der Doku.
7. Live-Ton im HA-Frontend ist die bekannte Schwachstelle. Braucht eine eigene Lösung (siehe VOX-Audio).

---

## 4. Zielbild und Abgrenzung

**Ziele**

- Vollwertiger Ersatz für ein Video-Babyphone im eigenen Heimnetz, ohne Cloudzwang.
- Wenige, verlässliche Alarme in drei Stufen statt vieler Bewegungsmeldungen.
- Einrichtung komplett über die Oberfläche (Config Flow), kein YAML für den Normalfall.
- Jede Entscheidung des Systems ist nachvollziehbar (Ereignisprotokoll mit Ursache).
- Zweisprachig Deutsch/Englisch wie bei KostalKore und InverterChargeNight.

**Nicht-Ziele**

- Kein Medizinprodukt, keine Diagnose, keine garantierte Erkennung.
- Kein eigener NVR: Aufzeichnung, Objekterkennung und Audioerkennung bleiben bei Frigate.
- Keine Reiselösung. Unterwegs bleibt ein einfaches Gerät sinnvoll.

**Voraussetzungen beim Nutzer**

- Home Assistant ab 2026.2 mit MQTT-Broker, Frigate (Mindestversion in Phase 0 festlegen, Vorschlag ≥ 0.16) mit go2rtc.
- Kamera mit RTSP **und** Audio (AAC), brauchbares Infrarot-Nachtbild, Montage möglichst senkrecht über dem Bett, Kabel außer Reichweite (mindestens 1 m).
- Companion-App auf den Eltern-Handys.
- Optional: Rechner mit GPU für ein lokales Bildmodell, mmWave-Radar, Raumklimasensor.

**Rahmenbedingungen dieses Projekts**

- Frigate-Rechner mit drei Außenkameras und Grafikeinheit ist vorhanden. Ob sie für ein lokales Bildmodell reicht, hängt von Typ und Grafikspeicher ab (eine integrierte Grafik genügt für Frigate, aber nicht für ein Bildmodell in brauchbarer Zeit); das wird in Phase 0 geklärt. Für das Kind kommt eine Innenkamera dazu, siehe Hardware unten.
- Das Kind kommt im Februar 2027 zur Welt, das System startet also mit einem **Neugeborenen**. Das hat Folgen:
  - In den ersten Monaten schläft das Kind empfohlenermaßen im Elternschlafzimmer (Beistellbett). Die Kamera hängt dann im Schlafzimmer der Eltern: Privatmodus per Taste und Zeitplan, kurze oder keine Aufzeichnung für diese Kamera. Hauptnutzen in dieser Zeit: abends und bei Tagschläfchen, wenn die Eltern in einem anderen Raum sind.
  - Mehrere Schlafplätze (Beistellbett, Stubenwagen im Wohnzimmer, später Kinderzimmer). Das Datenmodell ist deshalb „ein Kind, mehrere Schlafplätze", jeder mit eigener Kamera und eigenen Sensoren; der aktive Platz wird gewählt oder automatisch erkannt.
  - Neugeborene atmen unregelmäßig; Pausen bis etwa 10 Sekunden sind normal. Der Atem-Hinweis darf deshalb nicht unter 20 Sekunden auslösen und braucht den Schattenmodus besonders dringend.
  - Pucksack und Schlafsack verdecken Bewegung. Das schwächt die Videoerkennung und spricht für den Radarsensor als zweite Quelle.
  - Bis zur Geburt gibt es kein Kind zum Testen. Geprüft wird mit Puppe, Lautsprecher (Weinaufnahmen) und einem einfachen Atemsimulator; die Feinabstimmung folgt mit echten Daten im Schattenmodus.

**Hardware**

Kamera-Kandidaten (alle günstig, WLAN, Netzteil). Nicht jedes Modell einer Marke kann RTSP; entscheidend ist das genaue Modell.

| Kandidat | RTSP und Ton | Gegensprechen | Hinweise |
|---|---|---|---|
| UniFi G3 Instant (kleine WLAN-Kamera von Ubiquiti) | Über die Protect-Konsole, nicht direkt von der Kamera; in go2rtc als `rtspx://` | Nur in der Protect-App | 1080p, 111° Weitwinkel, Infrarot bis 6 m. Die Konsole wird Teil der Alarmkette und muss vom Watchdog mit überwacht werden. |
| Reolink E1 Pro / E1 Zoom (Schwenkkopf) | Direkt, Ton als AAC | Über go2rtc, modellabhängig | **Kauffalle:** Die einfache Reolink E1 kann RTSP/ONVIF nicht direkt, nur über Hub oder NVR. |
| TP-Link Tapo C200 / C210 / C120 | Direkt nach Aktivierung in der App | Über go2rtc (`tapo://`), je nach Firmware | Günstig; die App drängt zur Cloud, lässt sich aber ignorieren. |
| Eufy Innenkamera mit Schwenkkopf | Unklar | Unklar | Keine belastbaren Berichte mit Frigate gefunden. Nicht ohne eigenen Test kaufen. |

Auswahl in Phase 0 nach vier Kriterien, am besten im direkten Vergleich von zwei Kameras: (1) Ton im Stream, den Frigate auswerten kann, (2) Infrarotbild aus etwa 1 m Abstand ohne Überstrahlen, (3) Verzögerung von Bild und Ton, (4) Stabilität über 14 Tage.

Schwenkkopf: praktisch für mehrere Schlafplätze, aber nach jedem Schwenk stimmen Bett-Zone und Bildausschnitt der Atemerkennung nicht mehr. Deshalb fester Preset „Bett", und der Watchdog erkennt einen verstellten Blickwinkel.

Stückliste für den Vollausbau:

| Teil | Zweck | Phase |
|---|---|---|
| Innenkamera mit RTSP und Ton | Bild, Ton, Frigate-Erkennung | 0 |
| Türkontakt | „Jemand ist im Zimmer", später Kleinkind-Alarm | 1 |
| Sirene oder Lautsprecher im Elternschlafzimmer | Lokaler Alarmkanal ohne Internet | 1 |
| Temperatur-/Feuchtesensor | Raumklima | 1 |
| Seeed MR60BHA2 | Lokale Vitalquelle (Atmung, Puls) | 0 bestellen, 3 auswerten |
| Aqara FP2 | Lokale Präsenz/Zone, Vitaldaten experimentell über Cloud | 0 bestellen, 3 auswerten |
| ESP32 mit Summer | Dead-Man-Warnung, wenn Home Assistant ausfällt | 3 |
| USV für Server, Switch und Router (optional) | Überbrückt kurze Stromausfälle | beliebig |

---

## 5. Architektur

```mermaid
flowchart LR
  CAM[Kamera RTSP Audio+Video] --> G2R[go2rtc Restream]
  G2R --> FRI[Frigate: Bewegung, Audio, Zonen, Aufnahme]
  G2R --> ENG[Vital-Engine: Atem-Mikrobewegung]
  FRI -- MQTT --> INT
  ENG -- MQTT --> INT
  SEN[Optionale Sensoren: Radar, Klima, Tuer, Rauch/CO] -- HA-Entitaeten --> INT
  subgraph HA[Home Assistant]
    INT[Integration checkbaby]
    INT --> FUS[Signal-Fusion]
    FUS --> SM[Zustandsautomat Kind]
    SM --> ESC[Eskalationslogik]
    INT <--> AI[ai_task: Ollama lokal oder Gemini]
    WD[Watchdog] --> ESC
  end
  ESC --> PUSH[Companion-App: Info / Warnung / Kritisch]
  ESC --> OUT[Lautsprecher, Licht, Dead-Man-Summer]
```

### 5.1 Komponenten

**A. Integration `checkbaby` (HACS, `custom_components/`)** – das eigentliche Produkt. Orchestriert, rechnet aber nichts Schweres. `iot_class: local_push`, `integration_type: service`, ein Config-Eintrag pro Kind (Schlafplätze darunter, siehe 5.10).

**B. Vital-Engine (ab Phase 3, eigener Container/Add-on)** – zieht den Substream aus go2rtc, berechnet Atem-Mikrobewegung und veröffentlicht Ergebnis plus Signalqualität per MQTT. Bewusst getrennt von Home Assistant: Dauerhafte Videodekodierung im HA-Prozess gefährdet bei Fehlern oder Speicherlecks die gesamte Hausautomation. HACS kann keine Add-ons installieren; das Add-on-Repository kann aber im selben GitHub-Repo liegen, für HA-Container-Nutzer gibt es eine Compose-Datei. Ob Monorepo oder zweites Repo, klärt der Spike in Phase 0.

**C. Frigate** – unverändert, nur Konfigurationsempfehlung (Audio-Rolle, `listen: [crying, scream, yell]`, Zone „Bett").

### 5.2 Aufbau der Integration

Orientiert an InverterChargeNight: Home-Assistant-freie Logikmodule, die sich ohne HA testen lassen, und dünne Plattform-Dateien.

```
custom_components/checkbaby/
  __init__.py  config_flow.py  const.py  coordinator.py  entity.py
  sources/      frigate_mqtt.py, entity_source.py, engine_mqtt.py   (Signalquellen hinter einer Schnittstelle)
  fusion.py                 Signale -> Evidenz (reine Logik)
  state_machine.py          Kind-Zustand (reine Logik)
  escalation.py             Stufen, Quittierung, Schlummern, Sperrzeiten (reine Logik)
  notifier.py               iOS-/Android-Payloads, Aktionen, Anhänge
  ai/                       assessor.py, prompts.py, schema.py, budget.py
  watchdog.py               Herzschlag aller Quellen
  sleep_log.py              Schlafprotokoll (Store)
  binary_sensor.py sensor.py switch.py select.py number.py button.py event.py
  services.py services.yaml diagnostics.py icons.json strings.json translations/{de,en}.json
  quality_scale.yaml
```

### 5.3 Zustandsautomat

Zustände: `leer` · `schläft` · `unruhig` · `wach` · `weint` · `betreut` (Erwachsener im Bild, Alarme pausiert) · `unbekannt` (Signal unbrauchbar).

Übergänge hängen an Dauer und Kombination, nicht an Einzelereignissen. Beispiel: `schläft → unruhig` bei Bewegung über 20 s oder Laut über Schwelle; `unruhig → weint` erst bei `crying` über 8 s oder ansteigendem Pegel; zurück nach 2 min Ruhe. Alle Zeiten sind einstellbar und über Altersprofile vorbelegt (Neugeborenes, Säugling, Kleinkind).

### 5.4 Eskalationsmatrix (Startwerte)

| Auslöser | Quelle | Stufe |
|---|---|---|
| Bewegung im Schlaf, kurzes Quengeln | Frigate | Info (nur Protokoll/Dashboard) |
| Kind wach und ruhig | Bewegung + KI | Info, Push optional |
| Weinen anhaltend (Standard ≥ 15 s) | Audio | Warnung |
| Weinen unquittiert ≥ 3 min oder Schrei mit hoher Konfidenz | Audio | Kritisch |
| Kleinkind steht/klettert, verlässt Bett, Tür geht auf | Zone, KI, Türkontakt | Warnung bis Kritisch |
| Bauchlage (Altersprofil < 12 Mon.), Gesicht verdeckt | KI, zwei Prüfungen in Folge | Warnung, bei Bestätigung Kritisch |
| Lose Decke/Gegenstand im Bett | KI | Info/Warnung (Safe-Sleep-Hinweis) |
| Keine Atem- und Körperbewegung ≥ 20 s bei gültigem Signal | Engine und/oder Radar | Kritisch (erst nach Schattenmodus) |
| Raumtemperatur/Luftfeuchte außerhalb Bereich | Sensor | Info/Warnung |
| Rauch/CO im Kinderzimmer | Sensor | Kritisch (Durchreichung) |
| Überwachung ausgefallen (Kamera, Frigate, MQTT, Engine) | Watchdog | Warnung, im scharfen Zustand nach N min Kritisch |

**Stufen technisch:**

- **Info:** kein Ton, Eintrag im Protokoll.
- **Warnung:** normaler Push mit Schnappschuss und Aktionen (Gesehen · Schlummern 5 min · Live öffnen).
- **Kritisch:** iOS Critical Alert (`critical: 1`, volle Lautstärke) bzw. Android Alarm-Kanal (`channel: alarm_stream`, `priority: high`, `ttl: 0`), Wiederholung bis zur Quittierung, danach Eskalationskette: zweiter Elternteil → Lautsprecher/TTS → Licht im Elternschlafzimmer.

**Grundregeln:** Quittierung stoppt die Kette, nicht die Überwachung. Sperrzeiten gegen Alarmmüdigkeit gelten nie für Kritisch. „Wer hat Dienst?" steuert das erste Ziel, die Eskalation erreicht immer alle.

### 5.5 KI-Lagebewertung

- **Anbindung über `ai_task`** von Home Assistant. Der Nutzer wählt eine beliebige AI-Task-Entität (Ollama, Google Gemini, OpenAI …); wir liefern Anweisung, Bilder und ein festes Antwortschema. Damit pflegen wir keine Anbieter-SDKs und keine API-Schlüssel. Die Python-Schnittstelle und das Anhängen eigener Schnappschüsse sind in Phase 0 zu verifizieren (es gibt Forenberichte über Probleme mit Anhängen bei einzelnen Anbietern). Rückfallebene: direkter Anbieter-Client.
- **Anbieter:** Cloud über die Home-Assistant-Integrationen für Google Gemini und OpenRouter (beliebige Bildmodelle), lokal über Ollama. Welche Anhänge (Einzelbilder, Bildserie, kurzer Clip mit Ton) jeder Anbieter über `ai_task` wirklich annimmt, ist nicht dokumentiert und wird in Phase 0 ausprobiert. Die Modellauswahl wird mit Infrarotbildern getestet, weil Nachtbilder für Bildmodelle deutlich schwieriger sind.
- **Ausfallkette:** Cloud-Modell → lokales Modell (falls eingerichtet) → nur deterministische Stufe. Internetausfall darf nie zu „alles ok" führen.
- **Auslöser:** ereignisgesteuert (Weinen, Aufwachen, lange Reglosigkeit, Lagewechsel), periodischer Routine-Check im Schlafmodus (Standard alle 10 min), manuell per Button/Aktion.
- **Eingabe:** 3–4 Bilder über wenige Sekunden als Serie, dazu Kontext (Zustand, Schlafdauer, Pegel, Raumtemperatur, Altersprofil). Audio-Clips nur bei Modellen, die Audio verstehen.
- **Ausgabe (festes Schema):** `presence`, `position` (Rücken/Bauch/Seite/sitzt/steht/unklar), `face_visible`, `airway_risk` (keins/möglich/wahrscheinlich), `state`, `hazards[]`, `assessment` (ok/Hinweis/Warnung/kritisch), `confidence`, `reason` (ein Satz in Nutzersprache).
- **Leitplanken:**
  - KI allein löst höchstens „Warnung" aus. „Kritisch" nur bei definierter Gefahr und zweiter Prüfung mit frischem Bild (2 aus 2).
  - KI kann Info-Ereignisse still halten („dreht sich im Schlaf"), aber keine Warn-/Kritisch-Alarme aus deterministischen Quellen unterdrücken.
  - Zeitüberschreitung oder Fehler: Es gilt die deterministische Stufe, `binary_sensor.ki_verfuegbar` geht auf aus.
  - Budget: maximale Aufrufe pro Stunde, Sperrzeit zwischen Routine-Checks.
- **Datenschutz:** Der Nutzer wählt den Anbieter bei der Einrichtung. Cloud-Anbieter verlangen eine ausdrückliche Bestätigung mit dem Hinweis, dass Bilder des Kindes das Haus verlassen und je nach Tarif zum Training genutzt werden können (bei Gemini den bezahlten Tarif prüfen). Bilder werden nicht dauerhaft gespeichert, außer der Nutzer schaltet das Fehlersuch-Archiv ein.
- **Kosten:** Routine-Checks alle 10 Minuten ergeben rund 70 Aufrufe pro Nacht. Der tatsächliche Preis je Nacht wird in Phase 0 gemessen und als Sensor angezeigt; das Budget begrenzt ihn nach oben.

### 5.6 Vital-Engine (Atembewegungs-Hinweis)

- **Verfahren:** Bildausschnitt über dem Oberkörper (aus Bett-Zone, später automatisch), Graustufen, verkleinert, 5–10 Bilder/s. Bewegungssignal, Bandpass 0,3–1,5 Hz, Periodizität über 20–30 s Fenster, Signal-Rausch-Verhältnis als Konfidenz. Volle Eulerian Video Magnification ist laut Vorprojekten zu teuer; einfache Verfahren (Pixelintensität, optischer Fluss) reichen als Start.
- **Ausgabe:** `periodische_bewegung` · `grobe_bewegung` (Kind bewegt sich, Atmung nicht messbar, aber unkritisch) · `keine_bewegung` · `signal_unbrauchbar` (verdeckt, Kind nicht im Bild, Bildrauschen), dazu geschätzte Rate und Konfidenz.
- **Alarmbedingung:** Kind anwesend **und** Signal war zuvor gültig **und** weder periodische noch grobe Bewegung für ≥ 20 s. „Signal unbrauchbar" ist nie ein Alarm, sondern ein sichtbarer Zustand.
- **Fusion mit Radar:** Wenn ein mmWave-Sensor vorhanden ist, entscheidet einstellbar „eine Quelle genügt" (empfindlich) oder „beide Quellen" (weniger Fehlalarme).
- **Schattenmodus:** Mindestens zwei Wochen nur protokollieren, Trefferquote und Fehlalarme auswerten, erst dann Alarme freigeben. Der Schalter für den Atemalarm ist standardmäßig aus und trägt einen deutlichen Hinweistext.
- **Bekannte Grenzen:** Pucksack/dicke Decken, Seitenlage mit Rücken zur Kamera, Ventilator oder Mobile im Bildausschnitt, flacher Kamerawinkel, Bildrauschen bei Infrarot. Diese Liste gehört in die Nutzerdoku.

### 5.7 mmWave-Radar als zweite Vitalquelle

**Entschieden: Aqara FP2 und Seeed MR60BHA2 werden beide eingeplant und im Schattenmodus gegeneinander und gegen die Videoerkennung verglichen.** Der MR60BHA2 ist die lokale Vitalquelle mit Bauanleitung, der FP2 liefert lokal Präsenz und experimentell Vitaldaten.

| Sensor | Liefert Atmung/Puls? | Weg nach Home Assistant | Bewertung für uns |
|---|---|---|---|
| Aqara FP2 | Ja, im Schlafmodus (Atemrate, Herzrate, Schlafphase) | Lokal (HomeKit) kommt nur Präsenz an. Vitaldaten liegen in der Aqara-Cloud; ein Community-Add-on (SleepRadar) liest sie von dort aus | **Eingeplant:** lokal als Präsenz-/Zonensensor („liegt im Bett"). Vitaldaten über die Cloud nur als experimentelle Zusatzquelle, nie als alleiniger Alarmgrund: Cloud-Abhängigkeit, Auswertung für Erwachsene, Verzögerung unbekannt |
| Aqara FP300 | Nein (Präsenz, Licht, Temperatur, Feuchte; Batterie) | Zigbee/Thread/Matter | Nur als Präsenz- und Klimasensor brauchbar |
| Aqara FP400 | Nein (Präsenz, Zonen, Personenzahl) | Drittsysteme sehen nur Präsenz und Licht | Nicht geeignet |
| Seeed MR60BHA2 (60 GHz, mit ESP32-C6) | Ja: Atemrate, Herzrate, Abstand, Anzahl Ziele | ESPHome, direkt lokal, fertig geflasht lieferbar | **Eingeplant:** lokale Vitalquelle, Startpunkt der Bauanleitung |
| DFRobot C1001, HLK-LD6002 | Ja | UART, eigener ESP32 und Firmware nötig | Alternativen, falls der MR60BHA2 nicht taugt |
| Roh-Radar (z. B. Infineon BGT60TR13C) | Rohdaten, Auswertung selbst | Eigene Signalverarbeitung in der Vital-Engine | Ausbaustufe; in Studien und Abschlussarbeiten über dem Babybett erprobt |

**Was dabei ehrlich offen ist:** Alle fertigen Module sind für Erwachsene bei bis zu 1,5 m ausgelegt. Ein Neugeborenes hat einen viel kleineren Brustkorb, atmet 30–60-mal pro Minute und hat einen Puls von 100–160. Ob die Firmware des MR60BHA2 dafür plausible Werte liefert oder Bereiche abschneidet, steht in keiner Quelle und muss gemessen werden. Forschung an Frühgeborenen zeigt, dass Radar die Atmung von Säuglingen grundsätzlich erfassen kann, allerdings mit eigener Auswertung der Rohdaten und aus etwa 45 cm Abstand.

**Vorgehen:**

1. **Vor der Geburt:** beide Sensoren bestellen und montieren. Vortest an Erwachsenen gegen eine Referenz (Smartwatch oder Pulsoximeter): Stimmen Atemrate und Puls, wie schnell kommen die Werte an, wie verhält sich der FP2-Cloudweg bei Internetausfall? Außerdem prüfen, ob sich zwei 60-GHz-Sensoren am selben Bett gegenseitig stören.
2. **Ab Geburt:** beide im Schattenmodus neben der Videoerkennung. Vom MR60BHA2 wird zunächst nur die robuste Aussage „Ziel vorhanden und Atembewegung erkannt: ja/nein" genutzt, nicht die exakte Rate.
3. **Nach 14 Nächten:** Auswertung je Quelle (Verfügbarkeit, Aussetzer, Fehlalarme) und Entscheidung, welche Quellen in die Alarmlogik dürfen.
4. **Nur falls keine fertige Lösung beim Säugling trägt:** Roh-Radar mit eigener Auswertung in der Vital-Engine.

**Puls:** Die Herzbewegung ist beim Säugling noch einmal deutlich kleiner als die Atembewegung. Der Pulswert wird angezeigt und protokolliert, löst aber keinen Alarm aus, solange er nicht gegen ein Referenzgerät geprüft ist.

**Offene Schnittstelle:** Die Integration bindet Vitalquellen als frei zuordenbare Entitäten an (Atemrate, Herzrate, Präsenz, Aktualität). Wer einen FP2 über SleepRadar, ein Wearable oder einen anderen Sensor hat, kann ihn damit einhängen, ohne dass wir jeden Hersteller einzeln unterstützen.

**Bauanleitung (Teil der Doku):** Teileliste, Gehäuse und Halterung, Montagehöhe und Winkel, Kabelführung außer Reichweite des Kindes, ESPHome-Konfiguration, Prüfschritte. Der Dead-Man-Summer aus Abschnitt 5.8 kann auf derselben Platine sitzen, wenn das Gerät im Elternschlafzimmer steht.

### 5.8 Watchdog

- Herzschlag je Quelle: Kamerabild-Alter, Frigate `available`, MQTT-Verbindung, letzte Audiopegel-Meldung, Engine, KI-Erreichbarkeit, Push-Zustellbarkeit.
- Sammelsensor `binary_sensor.<kind>_ueberwachung_ok` plus Diagnosesensoren je Quelle.
- Testalarm-Button und optionaler täglicher Selbsttest (stille Zustellprüfung).
- **Internetausfall:** Push-Nachrichten laufen normalerweise über die Server von Apple und Google. Fällt das Internet aus, bleiben der lokale Push der Companion-App im Heim-WLAN (Verhalten bei kritischen Alarmen und auf Android in Phase 0 prüfen) und vor allem die rein lokalen Kanäle: Sirene oder Lautsprecher und Licht im Elternschlafzimmer. Der Watchdog überwacht die Internetverbindung und meldet, wenn nur noch lokale Kanäle verfügbar sind.
- **Externer Dead-Man:** Fällt Home Assistant selbst aus, kann es niemanden warnen. Lösung: kleines ESPHome-Gerät mit Summer im Elternschlafzimmer, das einen regelmäßigen Herzschlag erwartet und bei Ausbleiben selbst piept. Entspricht dem „Verbindung verloren"-Ton klassischer Babyphone.

### 5.9 Entitäten und Aktionen (Auszug)

| Typ | Entitäten |
|---|---|
| `sensor` | Zustand, Alarmstufe, Geräuschpegel, Atemrate (geschätzt) + Konfidenz, letzte Bewegung, Schlaf seit, Schlafdauer, Aufwachen heute Nacht, letzte KI-Bewertung, Lage |
| `binary_sensor` | weint, Bewegung, wach, im Bett, betreut, Atembewegung erkannt, Überwachung ok, KI verfügbar |
| `switch` | Überwachung scharf, KI-Bewertung, Atemalarm, VOX-Audio, Privatmodus |
| `select` | Modus (Aus/Nacht/Nickerchen/Babysitter), Empfindlichkeit, wer hat Dienst |
| `number` | Wein-Dauer bis Warnung, Pegelschwelle, Reglos-Zeit, KI-Intervall |
| `button` | Testalarm, KI-Check jetzt, Quittieren, Schlummern |
| `event` | Alarmereignisse für eigene Automationen |
| Aktionen | `assess_now`, `acknowledge`, `snooze`, `test_alert`, `start_sleep`, `end_sleep` |

### 5.10 Datenmodell und Einrichtung

**Datenmodell:** Ein Config-Eintrag je Kind. Darunter beliebig viele **Schlafplätze**, jeder mit Kamera, Bett-Zone und zugeordneten Sensoren (Radar, Klima, Tür). Genau ein Schlafplatz ist aktiv; gewählt per Auswahl oder automatisch dort, wo das Kind erkannt wird. Mehrere Kinder sind mehrere Einträge mit getrennten Zuständen und Zielen.

**Einrichtungsablauf (Config Flow):**

1. Kind: Name, Geburtsdatum (daraus das Altersprofil, das mit dem Alter automatisch weiterschaltet).
2. Schlafplatz: Frigate-Kamera wählen, Bett-Zone, optionale Sensoren zuordnen.
3. Benachrichtigung: Geräte der Eltern, Reihenfolge der Eskalation, lokaler Alarmkanal.
4. KI (optional): AI-Task-Entität wählen, bei Cloud-Anbietern Datenschutz bestätigen.
5. Hinweis zur Zweckbestimmung bestätigen (kein Medizinprodukt).
6. **Geführter Funktionstest:** Kommt Ton an? Wird eine abgespielte Weinaufnahme erkannt? Kommt der kritische Push trotz „Nicht stören" an? Geht die Sirene? Jeder Schritt wird abgehakt, Fehlendes erscheint als Reparaturhinweis.

Der Funktionstest lässt sich jederzeit wiederholen; eine monatliche Erinnerung ist einstellbar.

### 5.11 Betriebsanforderungen

| Anforderung | Zielwert (Start, wird in Phase 0/1 gemessen) |
|---|---|
| Anhaltendes Weinen bis Push auf dem Handy | Einstellbare Dauer plus höchstens 5 s |
| Ausfall einer Quelle bis Meldung | Höchstens 60 s |
| Schnell-Check bis Antwort | Ohne KI unter 2 s, mit KI unter 10 s |
| KI-Aufruf | Abbruch nach 20 s, dann gilt die deterministische Stufe |
| Zusatzlast auf dem HA-Rechner durch die Integration | Vernachlässigbar (keine Videoverarbeitung im HA-Prozess) |

- **Neustart:** Scharf-Zustand, laufende Alarme, Quittierungen und Schlafprotokoll überstehen einen Neustart. Nach dem Start gilt eine kurze Schonfrist, in der fehlende Quellen noch kein Alarm sind; danach greift der Watchdog normal.
- **Update-Wächter:** Wird Home Assistant oder Frigate neu gestartet oder aktualisiert, während die Überwachung scharf ist, gibt es vorher eine Warnung und nachher eine Meldung „Überwachung war X Minuten unterbrochen".
- **Zeit:** Alle Zeitlogik in UTC, Anzeige lokal; Sommerzeitwechsel ist ein eigener Testfall.

### 5.12 Datenschutz, Sicherheit, Recht

- **Netz:** Kamera ohne Internetzugang (Firewall-Regel oder eigenes Netzsegment), keine Portfreigaben, RTSP-Zugangsdaten nur in Frigate. Fernzugriff ausschließlich über den gesicherten Home-Assistant-Zugang.
- **Bilder in Benachrichtigungen:** Das Handy lädt Schnappschüsse von Home Assistant; von unterwegs braucht das die externe Adresse. Einstellbar ohne Bildvorschau auf dem Sperrbildschirm.
- **Speicherung:** Aufzeichnung und Aufbewahrungsdauer liegen bei Frigate; Empfehlung für die Kamera im Elternschlafzimmer ist keine oder sehr kurze Aufzeichnung. Die Integration speichert Ereignisprotokoll und Schlafdaten lokal, Bilder nur im ausdrücklich eingeschalteten Fehlersuch-Archiv.
- **Keine Telemetrie:** Das Projekt sendet nichts an uns oder Dritte. Einzige Ausnahme ist der vom Nutzer gewählte Cloud-KI-Anbieter.
- **Tonaufnahmen anderer Personen:** In Deutschland ist das heimliche Aufzeichnen nichtöffentlicher Gespräche strafbar (§ 201 StGB). Babysitter und Besuch müssen wissen, dass Kamera und Mikrofon laufen. Der Babysitter-Modus zeigt dazu einen Hinweis; die Doku erklärt es. Das ist ein Hinweis, keine Rechtsberatung.
- **Zweckbestimmung:** siehe Abschnitt 2.

---

## 6. Feature-Brainstorming

Legende: **M** = MVP (Phase 1), **2–5** = geplante Phase, **?** = Idee, noch zu bewerten.

**A. Gleichstand mit dem klassischen Babyphone**

- **M** Wein- und Geräuschalarm mit Dauer-/Trendlogik statt Lautstärkeschwelle
- **M** Live-Bild und Ton im Dashboard (go2rtc/WebRTC)
- **M** Verbindungs-/Ausfallalarm (Watchdog)
- **4** VOX-Audio: Kinderzimmerton automatisch auf einen Lautsprecher im Elternschlafzimmer legen, sobald es laut wird, und nach Ruhe wieder stumm schalten. Löst das Problem „Ton im HA-Frontend" und ist die Kernfunktion jedes Audio-Babyphones.
- **4** Gegensprechen über go2rtc (kameraabhängig)
- **4** Einschlafhilfe: Schlaflied/weißes Rauschen, Nachtlicht, Abschalt-Timer
- **4** Raumtemperatur und Luftfeuchte mit Empfehlungsbereich
- **M** Geräuschpegel-Anzeige als Ersatz für die LED-Leiste
- **4** Schwenken/Neigen und Presets, falls die Kamera es kann
- **4** Batteriewarnung für beteiligte Funksensoren
- **M** Schnell-Check „Wie geht es dem Kind?": ein Knopf, eine Aktion und ein Sprachbefehl liefern in wenigen Sekunden Zustand, aktuelles Bild, Pegel, Schlafdauer und (ab Phase 2) einen Satz KI-Einschätzung, als Antwort-Push oder Sprachausgabe
- **M** Mehrere Schlafplätze pro Kind mit Umschaltung

**B. Besser als ein Babyphone: Erkennung**

- **2** Safe-Sleep-Check per KI: Lage, Gesicht frei, lose Gegenstände
- **2** „Kind ist wach, aber zufrieden" von „braucht jemanden" unterscheiden
- **2** Betreuungserkennung: Erwachsener im Zimmer pausiert Alarme automatisch und schaltet danach wieder scharf
- **3** Atembewegungs-Hinweis aus Video, optional Radar
- **2** Kleinkind steht auf, klettert, verlässt das Bett; Türkontakt als zweites Signal
- **2** Husten-Erkennung und Hustenhäufigkeit pro Nacht (Audio-Label vorhanden)
- **3** mmWave-Radar nach Bauanleitung als zweite Vitalquelle (Abschnitt 5.7)
- **?** Frigate-Zustandsklassifikation (eigenes kleines Modell „Bett leer / schläft / wach") als lokale, schnelle Alternative zur KI für Standardfälle
- **?** Druck-/Belegungssensor unter der Matratze als weitere unabhängige Quelle
- **?** Wearables (z. B. Owlet über vorhandene Integration) als optionale Signalquelle
- **?** Schrei-Klassifikation (Hunger/Schmerz/Müdigkeit): Forschung existiert, Verlässlichkeit fraglich; höchstens als gekennzeichnetes Experiment
- **5** Luftqualität (CO₂) mit Lüftungshinweis; Rauch/CO-Durchreichung als Kritisch

**C. Benachrichtigung und Eskalation**

- **M** Drei Stufen mit kritischem Push, Schnappschuss, Aktionsknöpfen
- **M** Quittieren und Schlummern
- **2** Kurzer Clip mit Ton in der Benachrichtigung
- **4** „Wer hat Dienst?" mit Übergabe und Eskalation zum zweiten Elternteil
- **4** Stille Kanäle: Lampe im Elternschlafzimmer (Farbe je Stufe), Vibration auf der Smartwatch
- **4** Anwesenheitsabhängig: Tagsüber im Wohnzimmer TV-Einblendung oder Wandtablet statt Handyalarm
- **4** Babysitter-/Gästemodus: befristetes Zielgerät, vereinfachte Ansicht, konservativere Schwellen
- **M** Lokale Sirene im Elternschlafzimmer, wenn ein Alarm eine Minute unquittiert bleibt (nie im Kinderzimmer)
- **M** Türkontakt pausiert Meldungen, solange jemand im Zimmer ist
- **?** Telefonanruf als letzte Eskalationsstufe

**D. Schlaf-Analyse**

- **5** Automatisches Schlafprotokoll: Einschlafzeit, Aufwachphasen, Dauer, Zeit bis zur Beruhigung
- **5** Nachtbericht am Morgen als KI-Zusammenfassung mit Zeitleiste und Clips
- **5** Wochen- und Monatstrends, Zusammenhang mit Temperatur, Geräusch, Uhrzeit
- **5** Übergabe an Baby Buddy
- **?** Vorhersage „wacht vermutlich in 20 min auf" aus Unruhemustern

**E. Zuverlässigkeit und Betrieb**

- **M** Testalarm, Diagnose-Download, Ereignisprotokoll mit Ursache
- **M** Repair-Hinweise bei Fehlkonfiguration (kein Audio im Stream, `crying` nicht aktiviert, keine Critical-Berechtigung)
- **3** Dead-Man-Summer (ESPHome)
- **3** Schattenmodus für jede neue Erkennung
- **6** Wiedergabe-/Simulationsmodus: aufgezeichnete Szenarien einspielen, um Schwellen zu testen
- **M** Meldung bei Internetausfall und Umschaltung auf lokale Kanäle
- **2** Modell-Vergleich: derselbe beschriftete Szenensatz gegen mehrere KI-Modelle, damit ein Modellwechsel messbar besser ist
- **?** Doku-Empfehlungen: USV, Kamera per Firewall vom Internet trennen, Zweitgerät als Rückfallebene
- **?** Zugriff für Großeltern und Babysitter von außen (Fernzugriff, eingeschränktes Benutzerkonto)
- **?** Geschwister/Zwillinge: mehrere Kinder parallel, getrennte Zustände und Ziele

**F. Bedienung**

- **M** Beispiel-Dashboard (YAML) in Deutsch und Englisch
- **5** Eigene Karte mit Live-Bild, Zustand, Pegel und Quittier-Knopf (wird mit der Integration ausgeliefert)
- **M** Privatmodus (Erkennung und Benachrichtigung pausieren, z. B. beim Stillen)
- **4** Automatisch scharf: Zeitplan, „Kind im Bett + Tür zu", oder manuell
- **5** Blueprints für typische Automationen

**G. Zweite Ideenrunde**

*Erkennung und Zuverlässigkeit*

- **M** Kamera-Selbstüberwachung: Bild zu dunkel oder verdeckt, Blickwinkel verstellt, Infrarot ausgefallen, Mikrofon tot (Pegel dauerhaft flach)
- **M** Lernende Geräusch-Grundlinie: Weißes Rauschen oder ein Luftbefeuchter heben den Pegel dauerhaft an. Die Schwelle richtet sich nach dem gemessenen Grundpegel, ein Kalibrier-Assistent schlägt Startwerte vor.
- **M** Update- und Neustart-Wächter (Abschnitt 5.11)
- **M** Geführter Funktionstest mit monatlicher Erinnerung (Abschnitt 5.10)
- **2** Haustier im Bett: Frigate erkennt Katze oder Hund in der Bett-Zone
- **2** Meilenstein „dreht sich zum ersten Mal": Hinweis, dass ab jetzt nicht mehr gepuckt werden sollte und die Bauchlage-Regel sich ändert
- **2** Spucken/Erbrechen im Bild als KI-Prüfpunkt
- **?** Zeit in Bauchlage am Tag (beaufsichtigtes Üben) als Statistik

*Komfort im Haus*

- **4** Haus-Ruhemodus „Baby schläft": Türklingel leise oder nur aufs Handy, Durchsagen gedrosselt, Saugroboter pausiert, Fernseher-Lautstärke begrenzt; endet automatisch beim Aufwachen
- **4** Automatisches Nachtlicht (rot, stark gedimmt), wenn nachts jemand das Zimmer betritt
- **4** Raumklima aktiv regeln: Heizung und Luftbefeuchter, Hinweis bei offenem Fenster
- **4** Kleidungsempfehlung: passende Schlafsackstärke zur aktuellen Raumtemperatur
- **4** Lautstärkegrenze für weißes Rauschen
- **4** Tagsüber Durchsage auf Lautsprechern statt Handyalarm („weint seit zwei Minuten")

*Auswertung*

- **5** Wachfenster-Vorschlag: voraussichtlich nächste Schlafenszeit aus Alter und Schlafprotokoll
- **5** Wein-Statistik (Minuten pro Tag, Tageszeit), Zeit bis zur Beruhigung, was geholfen hat
- **5** Dienst-Statistik: wer hat nachts wie oft reagiert
- **5** Schnell-Protokoll per Taster, NFC-Aufkleber oder Benachrichtigungsknopf (Füttern, Windel), Weitergabe an Baby Buddy
- **5** Export für die Kinderarztpraxis (Schlaf-, Wein- und Hustenverlauf)
- **5** Erinnerungsalbum: Tagesbild oder Zeitraffer, auf Wunsch wählt die KI schöne Momente; nur lokal gespeichert

*Bedienung*

- **4** Smartwatch-Anzeige, Sperrbildschirm-Widget, Bild-in-Bild auf dem Fernseher, Wandtablet zeigt bei Alarm automatisch die Kamera
- **?** Zweiter Standort (z. B. Großeltern) als eigene Instanz mit denselben Benachrichtigungszielen

**Abdeckung klassischer Babyphone-Funktionen**

| Funktion eines Kauf-Babyphones | Bei uns | Phase |
|---|---|---|
| Ton mithören | VOX-Audio auf Lautsprecher, Live-Ton im Dashboard | 1 (Dashboard), 4 (Lautsprecher) |
| Bild, Nachtsicht | Kamera über go2rtc | 1 |
| Geräuschanzeige (LED-Leiste) | Pegelsensor und Anzeige | 1 |
| Geräuschalarm | Wein-/Schrei-Erkennung mit Dauerlogik | 1 |
| Reichweiten-/Verbindungsalarm | Watchdog, Dead-Man-Summer | 1, 3 |
| Gegensprechen | go2rtc, kameraabhängig | 4 |
| Schlaflieder, Nachtlicht | Automationen über Home Assistant | 4 |
| Temperaturanzeige | Raumklimasensor mit Bereichswarnung | 1 (Anzeige), 4 (Regelung) |
| Schwenken/Zoomen | Kamerafunktion, Preset „Bett" | 4 |
| Akku-Elterneinheit zum Mitnehmen | Handy; kein Ersatz für unterwegs | Nicht-Ziel |

---

## 7. Umsetzung in Phasen

**Zeitplan bis zur Geburt (Februar 2027).** Nach der Geburt ist kaum Entwicklungszeit; dann wird gemessen und nachjustiert, nicht neu gebaut.

| Zeitraum | Ziel |
|---|---|
| bis Mitte Dezember 2026 | Phase 0 abgeschlossen; Kamera und Radarmodul bestellt und montiert |
| bis Mitte Januar 2027 | Phase 1 (MVP) fertig, mit Puppe und Lautsprecher getestet, zwei Wochen Dauerlauf |
| bis zur Geburt | Phase 2 in Grundfunktion (Safe-Sleep-Check, Schnell-Check mit KI); Radar und Vital-Engine laufen im Schattenmodus mit |
| ab Geburt | Schattenbetrieb mit echten Daten, Schwellen anpassen, Entscheidung über Atem-Hinweis frühestens nach 14 Nächten |
| danach | Phasen 4 bis 6 nach Bedarf |

**Phase 0 – Fundament und Machbarkeit**

- Repo-Gerüst nach Vorlage InverterChargeNight: `custom_components/`, `hacs.json`, `manifest.json`, CI (pytest, mypy und pyright strikt, hassfest, HACS-Action, HA-Matrix älteste/neueste Version), `AGENTS.md`, Doku-Struktur `docs/de` und `docs/en`, Issue-Vorlagen, Coverage-Ratsche.
- Spikes am echten System:
  1. Frigate: Audio-Labels, MQTT-Payloads, Latenz Weinen → MQTT.
  2. `ai_task`: Aufruf aus Python, eigene Bildserien als Anhang, strukturiertes Ergebnis; Vergleich lokales Modell gegen Gemini mit Tag- und Infrarotbildern.
  3. go2rtc: Ton auf Lautsprecher (Format, Latenz), Substream für die Engine.
  4. Engine: Atemsignal aus aufgezeichnetem Testmaterial (Erwachsener, Puppe mit Motor) als Machbarkeitsbeweis.
- Entscheidungen aus Abschnitt 9 treffen.
- **Arbeitsteilung:** Das Repo-Gerüst und alle reinen Logikmodule entstehen ohne Hardware. Die Spikes 1 bis 3 brauchen das laufende Frigate, die Kamera und die Sensoren beim Projektinhaber; dafür liefert das Repo Prüfskripte und eine Checkliste, deren Ergebnisse als Spike-Notizen zurückfließen.
- **Fertig, wenn:** leere Integration installiert sich über HACS, CI ist grün, vier Spike-Notizen liegen vor.

**Phase 1 – MVP v0.1: klassisches Babyphone, nur verlässlicher**

Config Flow (Kind, Frigate-Kamera, Benachrichtigungsziele, Altersprofil), Frigate-Quelle, Zustandsautomat, Eskalation mit drei Stufen, Quittieren/Schlummern, Scharf/Unscharf und Modi, Watchdog, Testalarm, Diagnose, Beispiel-Dashboard, Übersetzungen.
**Fertig, wenn:** zwei Wochen Parallelbetrieb neben einem gekauften Babyphone ohne verpasstes Weinen und ohne unbemerkten Ausfall.

**Phase 2 – v0.2: KI-Lagebewertung**

`ai_task`-Anbindung, Schema, Leitplanken, Safe-Sleep-Check, Betreuungserkennung, Budget, Datenschutz-Opt-in, Clip in der Benachrichtigung.
**Fertig, wenn:** auf einem beschrifteten Testsatz eigener Szenen (Tag/Nacht) Trefferquote und Fehlalarmquote dokumentiert sind und die KI nachweislich keinen deterministischen Alarm unterdrücken kann (Tests).

**Phase 3 – v0.3: Vital-Engine im Schattenmodus**

Engine-Container/Add-on, MQTT-Vertrag, Fusion mit Radar, Dead-Man-Summer, Auswertung des Schattenbetriebs.
**Fertig, wenn:** Auswertung über mindestens 14 Nächte vorliegt und über die Freigabe des Alarms entschieden ist.

**Phase 4 – v0.4: Komfort**

VOX-Audio, Gegensprechen, Einschlafhilfe, Raumklima, Dienstplan, stille Kanäle, Babysitter-Modus, automatisches Scharfschalten.

**Phase 5 – v0.5: Schlaf-Analyse und Oberfläche**

Schlafprotokoll, Nachtbericht, Trends, Baby-Buddy-Anbindung, eigene Karte, Blueprints.

**Phase 6 – v1.0: Härtung und Veröffentlichung**

Szenario-Labor (Compose mit HA, Mosquitto, Frigate und go2rtc, das Testvideos als RTSP-Kamera einspielt), Quality Scale, vollständige zweisprachige Doku inklusive Grenzen und Hardwareliste, rechtliche Prüfung der Zweckbestimmung, Aufnahme in die HACS-Standardliste.

---

## 8. Qualität und Tests

- Logikmodule (`fusion`, `state_machine`, `escalation`, `ai/schema`) ohne HA-Abhängigkeit, mit Szenariotests aus aufgezeichneten Ereignisfolgen („Nacht mit dreimal Aufwachen", „Kamera fällt um 02:10 aus").
- Sicherheitsrelevante Invarianten als eigene Tests: KI unterdrückt keinen Alarm; Kritisch ignoriert Sperrzeiten; „Signal unbrauchbar" erzeugt nie „alles ok"; Ausfall jeder einzelnen Quelle führt zu einer Meldung.
- Strikte Typprüfung und Coverage-Ratsche wie in InverterChargeNight.
- Testmaterial: frei lizenzierte Audiodatensätze für Weinen, selbst gestellte Szenen. Keine echten Kinderaufnahmen im Repository.
- Jede neue Erkennung durchläuft den Schattenmodus, bevor sie alarmieren darf.

**Projektrahmen:** MIT-Lizenz wie die Schwesterprojekte; Doku zweisprachig mit gleichen Dateinamen in `docs/de` und `docs/en`; `CHANGELOG.md`; Issue-Vorlagen; Versionen über GitHub-Releases, damit HACS Updates anbietet; vor v1.0 Eintrag im Home-Assistant-Brands-Repo und Antrag für die HACS-Standardliste.

---

## 9. Risiken und offene Entscheidungen

| Risiko | Gegenmaßnahme |
|---|---|
| Falsche Sicherheit bei den Eltern | Klare Zweckbestimmung, Disclaimer im Setup, Zustand „unbekannt" sichtbar, Rückfallgerät empfohlen |
| Stiller Ausfall | Watchdog im MVP, Dead-Man-Summer, Selbsttest |
| Alarmmüdigkeit | Dauer-/Trendlogik, Altersprofile, Schattenmodus, KI filtert nur Info-Stufe |
| KI halluziniert oder fällt aus | Festes Schema, 2-aus-2 für Kritisch, deterministische Schicht bleibt führend |
| Kinderbilder in der Cloud | Lokal als Standard, ausdrückliches Opt-in, keine Dauerspeicherung |
| Infrarot-Nachtbild zu schlecht für Bildmodell oder Atemsignal | Früh in Phase 0 testen, Kamera- und Montageempfehlung |
| Frigate-/HA-Schnittstellen ändern sich | Quellen hinter einer Schnittstelle, CI gegen älteste und neueste HA-Version |
| Einstufung als Medizinprodukt | Wortwahl, keine Heilsversprechen, Prüfung vor v1.0 |

**Entschieden (21.11.2026):**

1. Name: Domain `checkbaby`, Anzeigename „CheckBaby – Smart Baby Monitor".
2. KI: Cloud (Gemini, OpenRouter) als Opt-in ist ausdrücklich gewünscht; lokal bleibt möglich. Alles außer der KI-Bewertung läuft lokal.
3. Frigate ist die zentrale Basis für Weinen, Schreien, Pegel und Bewegung. Die Atemstillstand-Erkennung schreiben wir selbst.
4. mmWave-Radar kommt als zusätzliche Quelle dazu. Aqara FP2 und Seeed MR60BHA2 werden beide eingeplant und verglichen (Abschnitt 5.7).
5. Erstes Altersprofil: Neugeborenes.
6. Kamera: günstige WLAN-Innenkamera; Kandidaten UniFi G3 Instant und Reolink mit Schwenkkopf (Abschnitt 4, Hardware).

**Noch offen:**

1. Vital-Engine als eigener Container/Add-on oder im HA-Prozess? *Empfehlung: eigener Container, endgültig nach dem Spike.*
2. Frigate direkt per MQTT oder über die Entitäten der Frigate-Integration? *Empfehlung: MQTT als Hauptweg, Entitäten als Rückfall.*
3. Welche Grafikeinheit steckt im Frigate-Rechner (Typ, Grafikspeicher)? Entscheidet, ob ein lokales Bildmodell als Rückfallebene bei Internetausfall möglich ist.
4. Genaues Kameramodell nach dem Vergleich in Phase 0. Bei UniFi: Läuft eine Protect-Konsole, und liefert ihr Stream den Ton so, dass Frigate ihn auswerten kann?

---

## 10. Quellen

- [AAP: aktualisierte Safe-Sleep-Empfehlungen 2022](https://www.aap.org/en/news-room/news-releases/aap/2022/american-academy-of-pediatrics-updates-safe-sleep-recommendations-back-is-best)
- [Frigate: Audio-Erkennung](https://docs.frigate.video/configuration/audio_detectors) · [MQTT](https://docs.frigate.video/integrations/mqtt) · [GenAI-Konfiguration](https://docs.frigate.video/configuration/genai/genai_config) · [Review-Zusammenfassungen](https://docs.frigate.video/configuration/genai/genai_review) · [Release 0.17](https://github.com/blakeblackshear/frigate/releases/tag/v0.17.0)
- [Frigate-Diskussion: Weinen nicht erkannt](https://github.com/blakeblackshear/frigate/discussions/10241) · [Beispielkonfiguration crying/scream/yell](https://github.com/blakeblackshear/frigate/issues/8171)
- [Home Assistant: AI Task](https://www.home-assistant.io/integrations/ai_task/) · [Entwicklerdoku](https://developers.home-assistant.io/docs/core/entity/ai-task) · [Forenbericht zu Bildanhängen](https://community.home-assistant.io/t/ai-task-generate-data-and-local-image-file-to-analyze/953555)
- [Companion-App: kritische Benachrichtigungen](https://companion.home-assistant.io/docs/notifications/critical-notifications)
- [Home Assistant Blog 2017: Smart Baby Monitor](https://www.home-assistant.io/blog/2017/02/03/babyphone/) · [FFmpeg Noise](https://www.home-assistant.io/integrations/ffmpeg_noise)
- [Forum: Baby monitor – any options to consider?](https://community.home-assistant.io/t/parents-baby-monitor-any-options-to-consider/664927)
- [CuboAI-Integration](https://github.com/niruse/cuboai) · [Baby Buddy für Home Assistant](https://github.com/jcgoette/baby_buddy_homeassistant)
- [CribSense](https://lukehsiao.github.io/CribSense) · [respmon](https://github.com/kevroy314/respmon) · [Vergleich von Verfahren zur Atemerkennung per Video](https://ar5iv.labs.arxiv.org/html/2211.16046)
- [ESPHome: Seeed MR60BHA2](https://esphome.io/components/seeed_mr60bha2/) · [DFRobot: Auswahlhilfe mmWave-Sensoren](https://www.dfrobot.com/blog-22042.html)
- [SleepRadar: Aqara-FP2-Vitaldaten über die Aqara-Cloud](https://community.home-assistant.io/t/sleepradar-aqara-fp2-sleep-vitals-heart-rate-breathing-rate-sleep-stage-as-home-assistant-mqtt-sensors/1016036) · [Aqara FP300](https://www.aqara.cn/eu/product/presence-multi-sensor-fp300) · [Aqara FP400 im Test](https://gizmodo.com/aqara-multi-sensor-fp400-review-not-quite-the-mmwave-of-the-future-2000804454)
- [Radar-Atemüberwachung bei Frühgeborenen (Scientific Reports 2022)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8956695/) · [Studienprotokoll FMCW-Radar für Säuglinge (2025)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11897680/)
- [Companion-App: lokaler Push](https://companion.home-assistant.io/docs/notifications/notification-local) · [Home Assistant: OpenRouter](https://www.home-assistant.io/integrations/open_router) · [Google Gemini](https://www.home-assistant.io/integrations/google_gemini)
- [UniFi G3 Instant](https://eu.store.ui.com/eu/en/products/uvc-g3-ins) · [Reolink E1-Familie: RTSP/ONVIF je Modell](https://www.smartrtsp.com/guides/reolink-e1-rtsp-onvif) · [Reolink E1 Pro/Zoom in Home Assistant](https://community.home-assistant.io/t/reolink-e1-zoom-and-or-pro-in-ha/276745) · [Tapo C200 in Frigate mit Ton](https://community.home-assistant.io/t/tapo-c200-setup-in-frigate-with-audio-ptz/812613)
- [localsmarthomeguide: Local baby monitor setup with Frigate and RTSP](https://localsmarthomeguide.com/articles/local-baby-monitor-setup-with-frigate-and-rtsp/) (vom Projektinhaber als Text bereitgestellt)

Hinweis zur Recherche: Der HA-Blogartikel von 2017 und der techdout-Artikel waren aus der Arbeitsumgebung nicht direkt abrufbar; ihr Inhalt ist über Suchergebnisse bzw. den mitgelieferten Reddit-Thread abgedeckt. Angaben zu Frigate, `ai_task`, lokalem Push und den Radarmodulen stammen aus Dokumentation und Suchergebnissen und werden in Phase 0 am laufenden System überprüft. Für Radarmodule an Säuglingen gibt es keine Herstellerangaben; hier zählt nur die eigene Messung.

---

## 11. Umsetzungsstand

Stand 21.11.2026. „Getestet" heißt hier: durch automatische Tests abgedeckt, die gegen Home Assistant 2026.2 und 2026.10 laufen. **Nichts davon ist bisher an einer echten Kamera, einem echten Frigate, einem Handy oder einem Radarsensor gelaufen.** Die MQTT-Themen, das Format der Push-Nachrichten und der Aufruf der KI stammen aus Dokumentation und Recherche; ob sie an deinem System genau so stimmen, zeigt erst die Checkliste.

### Umgesetzt und getestet

| Bereich | Was es tut |
|---|---|
| Einrichtung | Dialog für Kind, ersten Schlafplatz, Benachrichtigungsziele und Zweckbestimmung; weitere Schlafplätze als Untereinträge; Optionen; Reparaturhinweise bei fehlendem Ziel, fehlendem Schlafplatz, fehlendem MQTT |
| Quellen | Frigate über MQTT (Weinen, Schrei, Pegel, Bewegung, Person, Katze/Hund in der Bett-Zone, Verfügbarkeit); alternativ Entitäten für Weinen, Bewegung und Pegel; Präsenz, Türkontakt, Raumklima, Rauch/CO, Internet |
| Zustand | Leer, schläft, unruhig, wach, weint, betreut, unbekannt; Übergänge nach Dauer, nicht nach Einzelereignis |
| Alarme | Hinweis, Warnung, kritisch; Wiederholung, Eskalation an alle, lokaler Alarmkanal, Quittieren, Schlummern, Sperrzeit; alle Regeln der Eskalationsmatrix aus 5.4 |
| Benachrichtigung | Push mit Bild und Knöpfen für iOS und Android in einer Nachricht, kritische Alarme mit Durchbruch durch „Nicht stören"; „Wer hat Dienst"; Babysitter-Modus |
| Ausfallüberwachung | Jede Quelle einzeln, flaches Mikrofon, fehlendes Benachrichtigungsziel; Meldung nach Unterbrechung und beim Herunterfahren; Herzschlag-Tasten für einen Dead-Man-Summer |
| Geräusch-Grundlinie | Lernt den Raumpegel, auch ein dauerhaft laufendes weißes Rauschen |
| KI-Bewertung | Aufruf über `ai_task` mit Kamerabild und festem Antwortschema; Ausweichkette, Zeitlimit, Stundenbudget, Einwilligung; alle Leitplanken aus 5.5 |
| Atembewegungs-Hinweis | Regel mit Radar-Entität und Vital-Engine als Quellen, Fusion, Schattenmodus, Untergrenze 20 s |
| Komfort | Ton-Weiterleitung auf einen Lautsprecher (VOX), Schlafsack-Empfehlung, Ruhezeit-Sensor für eigene Automationen, Privatmodus, mehrere Schlafplätze |
| Auswertung | Schlafprotokoll, Aufwachen, Weinzeit, Schnell-Check und Nachtbericht als Knopf und als Aktion mit Rückgabewerten |
| Betrieb | Einstellungen, Alarme und Schlafprotokoll überstehen Neustarts; Diagnose-Download ohne Daten des Kindes; Ereignisprotokoll jeder Entscheidung |

### Geschrieben, aber nur eingeschränkt prüfbar

- **Vital-Engine** (`engine/`): eigener Dienst für die Atem-Mikrobewegung aus dem Videobild, mit 189 eigenen Tests. Geprüft mit künstlichen Signalen, als Container gegen einen echten MQTT-Broker und gegen einen künstlichen RTSP-Videostrom. Ungeprüft: jede echte Kamera, go2rtc als Quelle, das Add-on-Paket. Alle Schwellen sind nur an künstlichen Bildern eingestellt. Details und Grenzen in `engine/README.md`.
- **Verzögerung des Atembewegungs-Hinweises über die Engine:** Die Engine meldet „keine Bewegung" bauartbedingt erst 18 bis 21 Sekunden nach dem letzten Atemzug, danach wartet die Integration die eingestellte Zeit (mindestens 20 Sekunden). Zusammen sind das rund 40 Sekunden. Ob das verkürzt werden kann, ohne Fehlalarme zu erzeugen, lässt sich erst mit echten Daten aus dem Schattenmodus entscheiden.
- **Beispiele** (`docs/examples/`, `blueprints/`): Dashboard, Frigate-Konfiguration, ESPHome für Radar und Dead-Man-Summer, Automations-Vorlagen. Syntaktisch geprüft, nie auf einem Gerät gelaufen.

### Abweichungen vom Plan

- **Schrei** zählt wie Weinen mit kürzerer Bestätigungszeit und wird nicht sofort kritisch. Sonst würde heftiges Weinen ständig kritische Alarme auslösen; kritisch wird es über die Regel „unbeantwortet seit drei Minuten".
- **KI bekommt ein Einzelbild**, keine Bildserie. `ai_task` liefert pro Kamera nur das aktuelle Bild. Die Bestätigung läuft über einen zweiten Blick nach 15 Sekunden.
- **Bauchlage** wird nur beim Neugeborenen nach Bestätigung kritisch, beim Säugling bleibt sie eine Warnung, weil sich ältere Säuglinge selbst drehen dürfen.
- **Ein unsicheres „alles in Ordnung" der KI** nimmt eine KI-Warnung nicht zurück.
- **Stille nach einer großen Bewegung zählt nicht als „keine Atembewegung".** Wer das Kind herausnimmt, erzeugt genau dieses Muster: Bewegung, dann nichts. Ohne Präsenzsensor ließe sich ein leeres Bett sonst nicht von einem Atemstillstand unterscheiden und würde jeden Morgen einen kritischen Alarm auslösen. Die Quelle muss erst wieder Atmung sehen, bevor Stille zählt; dasselbe gilt, nachdem jemand beim Kind war. Der Preis: Ein Aussetzen direkt nach einer großen Bewegung wird nicht erkannt, bis wieder Atmung gesehen wurde. Ein Präsenzsensor für das Bett bleibt die bessere Lösung.
- **Ein Radarwert, der zwei Minuten nicht neu gemeldet wurde, gilt als Störung**, nicht als fortgesetzte Atmung.
- **Schlummern verschiebt die Frist „niemand reagiert"** beim Weinen: Wer „5 min Ruhe" drückt, hat reagiert.
- **Der Privatmodus sperrt jeden KI-Aufruf**, auch den von Hand ausgelösten.
- **Mindestversion** ist Home Assistant 2026.2, weil gegen ältere Versionen nicht getestet wird.

### Noch nicht umgesetzt

| Punkt aus dem Plan | Stand |
|---|---|
| Prüfungen am echten System (Phase 0) | Offen, brauchen deine Hardware |
| Geführter Funktionstest im Einrichtungsdialog | Nicht gebaut; es gibt den Testalarm-Knopf und die Checkliste |
| Warnung *vor* einem Update oder Neustart | Nicht gebaut; gemeldet wird beim Herunterfahren und nach der Unterbrechung |
| Kalibrier-Assistent für Schwellen | Nicht gebaut; die Grundlinie lernt selbst |
| Sprachbefehl „Wie geht es dem Kind?" | Nicht als eigener Befehl; die Aktion `quick_check` lässt sich in ein Skript für den Sprachassistenten legen |
| Husten-Erkennung, Meilenstein „dreht sich", Spucken | Nicht gebaut |
| Eigene Dashboard-Karte | Nicht gebaut; es gibt ein Beispiel-Dashboard aus Standardkarten |
| Baby-Buddy-Anbindung, Schnell-Protokoll, Export, Erinnerungsalbum, Wachfenster, Dienst-Statistik | Nicht gebaut |
| Raumklima aktiv regeln, Nachtlicht, Einschlafhilfe | Nicht gebaut; der Ruhezeit-Sensor und das Alarm-Ereignis sind die Bausteine für eigene Automationen |
| Telefonanruf als Eskalation, Smartwatch, Fernseher | Nicht gebaut |
| Modell-Vergleich mit eigenem Szenensatz | Nicht gebaut; braucht echte Bilder vom Schlafplatz |
| Szenario-Labor mit echtem Frigate | Nicht gebaut |
| Roh-Radar mit eigener Auswertung | Nicht gebaut, laut Plan nur falls die fertigen Sensoren nicht tragen |
| Markenbilder, HACS-Standardliste, rechtliche Prüfung | Vor v1.0 |

### Was als Nächstes zählt

1. Checkliste am echten System durchgehen. Sie entscheidet, ob MQTT-Themen, Push-Format und KI-Aufruf stimmen.
2. Zwei Wochen Parallelbetrieb neben einem gekauften Babyphone, mit ausgeschaltetem Atembewegungs-Alarm.
3. Erst danach Schwellen anpassen und über den Atembewegungs-Alarm entscheiden.

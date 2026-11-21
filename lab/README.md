# CheckBaby-Labor

Ein echtes Home Assistant, in dem CheckBaby ohne Kamera, Handy und Radar ausprobiert werden kann.
Gedacht für zwei Dinge: Fehler finden, bevor Hardware da ist, und Verhalten ansehen, statt es nur zu lesen.

## Was echt ist und was simuliert

| Echt | Simuliert |
|---|---|
| Home Assistant (aktuelle Version), ohne Mocks | Frigate: `frigate_sim.py` veröffentlicht die MQTT-Nachrichten, die Frigate laut Doku sendet |
| Die Integration aus diesem Checkout, unverändert | Handys: Benachrichtigungsdienste, die jede Nachricht aufzeichnen |
| Mosquitto als MQTT-Broker und die MQTT-Integration | Sensoren: Radar, Raumklima, Tür, Präsenz, Rauch, Internet |
| Einrichtung über dieselbe HTTP-Schnittstelle wie die Oberfläche | Kamera: eine Zeichnung statt eines Bildes |
| Home Assistants `ai_task` samt Auflösen des Kamerabilds | Das KI-Modell: antwortet nach Drehbuch |
| Die Vital-Engine als eigener Prozess | Ihr Videobild: das eingebaute Testmuster |
| Echtzeit: eine Minute dauert eine Minute | |

**Was das Labor deshalb nicht beweist:** dass ein echtes Frigate genau diese Themen und Werte sendet, dass
eine Push-Nachricht auf einem echten Handy ankommt und trotz „Nicht stören" ertönt, dass ein echtes KI-Modell
ein Kamerabild richtig beurteilt, und dass Radar oder Vital-Engine bei einem Kind brauchbare Werte liefern.
Dafür gibt es die [Checkliste für das echte System](../docs/development/phase-0-checkliste.md).

## Voraussetzungen

- Python 3.14 (das verlangt das aktuelle Home Assistant)
- Mosquitto: unter Debian/Ubuntu `apt-get install mosquitto`
- Einmalig die Umgebung anlegen:

```bash
uv venv --python 3.14 .venv-lab
```

```bash
uv pip install --python .venv-lab/bin/python -r lab/requirements.txt
```

Beim ersten Start lädt Home Assistant die Pakete der benutzten Integrationen selbst nach.

## Abnahmelauf ohne Oberfläche

```bash
.venv-lab/bin/python lab/check_lab.py
```

Dauert etwa neun Minuten, weil die Abläufe in Echtzeit durchlaufen werden (ein lokaler Alarm kommt nach einer
Minute, also wartet der Lauf eine Minute). Am Ende steht, wie viele Prüfungen bestanden wurden; das Ergebnis
liegt auch in `lab/reports/latest.json`. Jeder Lauf beginnt in einem leeren, temporären Home Assistant.

| Szenario | Was geprüft wird |
|---|---|
| Einrichtung | Alle Dialoge über die Frontend-Schnittstelle: Kind, Schlafplatz, Ziele, Zweckbestimmung, Optionen, zweiter Schlafplatz |
| Grundzustand | Ton kommt über MQTT an, Zustand „schläft", keine Meldung bei Ruhe |
| Nachrichtenflut | 40 MQTT-Nachrichten pro Sekunde bremsen nichts |
| Weinen | Warnung an das Handy im Dienst, Bild abrufbar, Ton-Weiterleitung, lokaler Alarm nach einer Minute, kritisch an alle, Wiederholung, „Gesehen", Ende nach Ruhe |
| Frigate-Ausfall | Frigate offline, Kamera ohne Ton, jeweils Meldung und Erholung |
| Broker-Neustart | MQTT-Störung wird gemeldet, nach dem Neustart läuft alles von selbst weiter |
| KI-Bewertung | Echter `ai_task`-Aufruf mit Kamerabild, Warnung, zweiter Blick, kritisch, Entwarnung, Fehler, Privatmodus |
| Atembewegung | Herausheben löst nichts aus, Stillstand nach gesehener Atmung wird kritisch, Radar ohne Wert ist eine Störung |
| Vital-Engine | Echter Engine-Prozess meldet das Testmuster, Absturz wird gemeldet |
| Rauch und Internet | Rauch trotz ausgeschalteter Überwachung, lokaler Alarm sofort ohne Internet |
| Berichte | Schnell-Check, Nachtbericht, Herzschlag, Diagnose ohne Namen des Kindes |
| Neustart | Zustand auf der Platte, Einstellungen und Schlafprotokoll nach dem Neustart |

Mit `--long` wartet der Lauf vor dem Neustart zusätzlich zwei Minuten und prüft die Meldung „war unterbrochen".
Mit `--only crying_chain ai_assessment` laufen nach Einrichtung und Grundzustand nur die genannten Szenarien.
`reports_and_diagnostics` setzt die vorherigen Szenarien voraus (Schlafzeit, Herzschlag) und schlägt allein gestartet fehl.

## Labor zum Anfassen

```bash
.venv-lab/bin/python lab/run_lab.py
```

Öffnet Home Assistant auf <http://127.0.0.1:8123>. Beim ersten Start legst du dort einen Benutzer an. Das Kind
„Baby" ist schon eingerichtet, das Dashboard „CheckBaby" steht in der Seitenleiste. Im Terminal läuft eine
Konsole, mit der du Ereignisse auslöst:

```text
lab> cry on            Frigate hört Weinen
lab> tap seen          ein Elternteil tippt „Gesehen"
lab> breath 0          das Radar sieht keine Atembewegung mehr
lab> door open         jemand kommt ins Zimmer
lab> ai risky          die KI meldet beim nächsten Blick ein Risiko
lab> offline           Frigate fällt aus
lab> pushes            was die simulierten Handys bekommen haben
lab> status            was CheckBaby gerade sieht
```

Zuerst den Schalter „Monitoring" einschalten, sonst meldet CheckBaby nur Rauch und Testalarme. Der Stand liegt
in `lab/runtime` und bleibt zwischen den Starts erhalten; den Ordner löschen heißt neu anfangen.

`frigate_sim.py` lässt sich auch allein gegen einen beliebigen Broker starten, zum Beispiel um ein echtes
Home Assistant ohne Frigate zu füttern.

## Aufbau

- `labkit.py`: Broker, Start von Home Assistant, HTTP-Zugriff
- `frigate_sim.py`: der Frigate-Ersatz
- `custom_components/checkbaby_lab/`: die simulierten Geräte. Diese Integration gehört nur ins Labor.
- `check_lab.py`: der Abnahmelauf
- `run_lab.py`: das Labor zum Anfassen

## Was das Labor schon gefunden hat

Fehler, die erst im echten Home Assistant sichtbar wurden und behoben sind:

- Nach jedem Start stand der Zustand 20 Sekunden lang auf „betreut", weil eine geschlossen gemeldete Tür wie
  eine gerade geschlossene aussah.
- Ein Radar ohne Messwert führte zu einer Störungswarnung, die kritisch wurde, obwohl der
  Atembewegungs-Alarm ausgeschaltet war.
- Der Schritt von Warnung zu kritisch startete die Minute bis zum lokalen Alarm neu.
- Bei kurzer Warnzeit meldete die Nachricht „weint", während der Zustand noch „schläft" zeigte.

Und eine Falle im Labor selbst, die auch andere Labore trifft: Home Assistant ab 2026.11 behandelt einen
`http:`-Block aus YAML als Probelauf und startet sich fünf Minuten nach dem Start neu, wenn er nicht
bestätigt wird. `labkit.py` bestätigt ihn deshalb direkt nach dem Start.

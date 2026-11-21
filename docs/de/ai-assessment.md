# KI-Bewertung

[English version](../en/ai-assessment.md) · [Zurück zur Übersicht](README.md)

Die KI-Bewertung ist optional. Sie schaut auf ein Standbild des Bettes und beantwortet eine feste Liste von Fragen: Ist das Kind da, wie liegt es, ist das Gesicht frei, liegen lose Gegenstände im Bett. Alles andere, auch jeder Wein-Alarm und die Ausfallüberwachung, funktioniert ohne sie und ohne Internet.

Der Aufruf der KI wurde nur gegen eine simulierte KI-Aufgabe getestet. Welche Anbieter über AI Task von Home Assistant ein Kamerabild annehmen und wie gut ein Modell ein Infrarot-Nachtbild beurteilt, wurde noch nicht ausprobiert. Prüfe das Ergebnis mit einer Puppe, bevor du ihm Gewicht gibst.

## Wofür die KI nicht verwendet wird

**Die KI prüft nicht die Atmung.** Ein Sprach- und Bildmodell sieht einzelne Standbilder, braucht Sekunden für eine Antwort und kann überzeugend falsch liegen. Atmung ist eine winzige periodische Bewegung, für die es ein durchgehendes Signal braucht. Der [Atembewegungs-Hinweis](vital-sources.md) kommt deshalb von einem Radarsensor oder der Vital-Engine, nie von der KI. Wird „keine Atembewegung" erkannt, bittet CheckBaby die KI zwar um einen Blick als zusätzliche Information. Was auch immer die KI antwortet, kann diesen Alarm aber weder löschen noch herabstufen.

Der Eindruck der KI, ob das Kind schläft oder weint, wird mit der Antwort gespeichert und nicht verwendet. Der Zustand des Kindes kommt aus Frigate und deinen Sensoren.

## Einrichten

1. Richte in Home Assistant eine Integration ein, die eine **AI-Task-Entität** (KI-Aufgabe) bereitstellt, zum Beispiel Google Gemini, OpenRouter oder Ollama.
2. Sorge dafür, dass der Schlafplatz eine **Kamera-Entität** hat. Von ihr stammt das Bild.
3. Öffne die Optionen des CheckBaby-Eintrags.
4. Wähle unter **KI-Aufgaben, in bevorzugter Reihenfolge** eine oder mehrere Entitäten.
5. Kreuze **Bilder des Kindes dürfen an diese KI-Aufgaben gesendet werden** an. Ohne das lassen sich die Optionen nicht speichern, solange KI-Aufgaben gewählt sind.
6. Stelle **KI-Aufrufe pro Stunde höchstens** ein (1 bis 120, Standard 30).
7. Schalte am Gerät den Schalter **KI-Bewertung** ein. Er ist standardmäßig aus.

## Was gesendet und was gefragt wird

Jede Bewertung ist ein Aufruf von `ai_task.generate_data` mit:

- **einem Standbild** der Kamera-Entität des aktiven Schlafplatzes,
- einer englischen Anweisung, die dem Modell sagt, nur zu berichten, was sichtbar ist, und „unknown" zu antworten, statt zu raten,
- dem Altersprofil und dem Zustand, den die Überwachung gerade anzeigt,
- einer festen Antwortstruktur.

Das Modell muss diese Felder ausfüllen:

| Feld | Mögliche Antworten |
|---|---|
| `presence` | `in_bed` (im Bett), `not_visible` (nicht zu sehen), `caregiver_present` (Betreuungsperson da) |
| `position` | `supine` (Rücken), `prone` (Bauch), `side` (Seite), `sitting`, `standing`, `unknown` |
| `face_visible` | ja / nein: Nase und Mund sind sichtbar und unbedeckt |
| `airway_risk` | `none` (keins), `possible` (möglich), `likely` (wahrscheinlich); „likely" nur, wenn Nase und Mund klar verdeckt sind oder in Bettzeug gedrückt werden |
| `state` | `asleep`, `awake_calm`, `awake_restless`, `crying`, `unknown` |
| `hazards` | lose Gegenstände im Bett (Decke, Kissen, Spielzeug, Schnur); optional |
| `view_ok` | nein, wenn das Bild zu dunkel oder verdeckt ist oder kein Bett zeigt |
| `assessment` | Gesamturteil: `ok`, `attention`, `warning`, `critical` |
| `confidence` | 0 bis 1 |
| `reason` | ein kurzer Satz in der Sprache deines Home Assistant |

Die Antwort gilt als nicht vertrauenswürdig. Fehlt ein Pflichtfeld, wird die ganze Antwort verworfen. Ein Wert, der nicht in der Liste steht, wird durch die vorsichtige Wahl ersetzt: Ein unlesbarer Atemwegs-Wert wird zu „possible", nie zu „none".

Der Plan sah eine Serie von drei oder vier Bildern vor. AI Task liefert je Kamera ein aktuelles Bild; die Bestätigung läuft deshalb über einen zweiten Blick nach 15 Sekunden.

## Wann sie läuft

Automatische Bewertungen brauchen all das: Überwachung an, Privatmodus aus, Schalter „KI-Bewertung" an, KI-Aufgaben und Einwilligung in den Optionen, eine Kamera-Entität, und das Kind ist nicht „Betreut".

| Auslöser | Wann |
|---|---|
| Zustandswechsel | Der Zustand wird „Weint" oder „Wach". |
| Keine Atembewegung | Die Regel für die Atembewegung beginnt zu gelten, auch im Schattenmodus. |
| Routine | Alle 10 Minuten (Zahl „Abstand der KI-Routineprüfung", 2 bis 60 Minuten), gezählt ab der letzten automatischen Bewertung. |
| Zweiter Blick | 15 Sekunden nach einer Bewertung, die eine Atemwegs- oder Bauchlage-Warnung oder ein erstes „Kamerablick verdeckt" ergeben hat. Nur einmal; ein zweiter Blick plant nie einen dritten. |
| Von Hand | Die Taste „KI-Check jetzt", die Aktion `checkbaby.assess_now` oder `checkbaby.quick_check` mit `with_ai`. |

Es läuft immer nur eine Bewertung gleichzeitig.

Eine Bewertung von Hand wird ausgeführt, sobald KI-Aufgaben, Einwilligung und eine Kamera-Entität eingerichtet sind. Sie beachtet weder den Schalter „KI-Bewertung" noch das Budget, den Privatmodus oder die Frage, ob die Überwachung an ist. Solange die Überwachung aus oder der Privatmodus an ist, wird ihr Ergebnis angezeigt, löst aber keinen Alarm aus.

## Budget, Zeitlimit und Ausweichkette

- **Budget:** höchstens die eingestellte Zahl von Aufrufen in beliebigen 60 Minuten. Ist es verbraucht, entfallen automatische Bewertungen, bis Aufrufe aus der Stunde herausfallen. Bewertungen von Hand werden immer ausgeführt und zählen zum Budget. Der Sensor „KI-Aufrufe in der letzten Stunde" zeigt den Stand. Bei einer Routineprüfung alle 10 Minuten kannst du mit etwa 6 Aufrufen pro Stunde rechnen, dazu die ereignisgesteuerten; die Kosten hängen von deinem Anbieter ab.
- **Ausweichkette:** Die KI-Aufgaben werden in der Reihenfolge gefragt, die du gewählt hast. Die erste verwertbare Antwort gilt. So setzt du ein Cloud-Modell an die erste und ein lokales an die zweite Stelle, oder umgekehrt.
- **Zeitlimit:** Jede KI-Aufgabe hat 20 Sekunden. Eine Zeitüberschreitung, ein Fehler oder eine unbrauchbare Antwort führt zur nächsten Aufgabe.
- **Wenn keine antwortet:** Der Binärsensor „KI-Bewertung verfügbar" geht aus, und sonst ändert sich nichts. Die deterministischen Alarme arbeiten wie zuvor. Eine KI, die nicht erreichbar ist, führt nie zu „alles in Ordnung".

Eine Bewertung zählt als ein Aufruf im Budget, egal wie viele KI-Aufgaben dafür versucht werden mussten.

## Was die KI darf: die Leitplanken

Die KI kann nur vier eigene Alarme anlegen, ändern und löschen: **Risiko für die Atemwege**, **Bauchlage**, **Lose Gegenstände im Bett** und **Kamerablick verdeckt**. Einen Alarm aus einer anderen Quelle kann sie nicht anfassen. Eine KI-Antwort „alles in Ordnung" während des Weinens, einer Störung der Überwachung oder „keine Atembewegung" ändert an diesen Alarmen nichts.

„Sicher" heißt unten: Konfidenz von mindestens 0,5. „Bestätigt" heißt: Die Bewertung davor, höchstens 180 Sekunden früher, hat dasselbe gesagt.

| Was die KI meldet | Ergebnis |
|---|---|
| Kind im Bett, Atemwegs-Risiko „likely", sicher | **Warnung.** **Kritisch**, sobald der zweite Blick es bestätigt. |
| Kind im Bett, Atemwegs-Risiko „possible", oder „likely", aber nicht sicher | Hinweis |
| Kind im Bett, Lage „prone", Profil Neugeborenes | **Warnung**, wenn sicher, sonst Hinweis. **Kritisch**, sobald bestätigt. |
| Kind im Bett, Lage „prone", Profil Säugling | **Warnung**, wenn sicher, sonst Hinweis. Nie kritisch: Ältere Säuglinge dürfen sich selbst drehen. |
| Lage „prone", Profil Kleinkind | Nichts |
| Lose Gegenstände genannt | Hinweis, mit den Gegenständen in den Einzelheiten des Alarms |
| Blick nicht in Ordnung | Hinweis; **Warnung**, sobald bestätigt |

Allein, mit einem einzigen Bild, erreicht die KI also höchstens eine Warnung. Kritisch braucht zwei Bewertungen in Folge, die dieselbe definierte Gefahr sehen.

Ein KI-Alarm endet, wenn eine spätere Bewertung seine Ursache nicht mehr meldet, und er sinkt auf eine niedrigere Stufe, wenn eine spätere Bewertung die Ursache als weniger ernst meldet. Eine Ausnahme: Eine Bewertung, die nicht sicher ist und gar nichts meldet, kann eine KI-Warnung oder einen kritischen KI-Alarm nicht zurücknehmen. Die KI-Alarme werden außerdem gelöscht, wenn die Überwachung ausgeschaltet, der Privatmodus eingeschaltet wird oder jemand beim Kind ist.

Einmal ausgelöst, verhält sich ein KI-Alarm wie jeder andere Alarm seiner Stufe: Ein kritischer geht an alle Handys, wiederholt sich alle 30 Sekunden und schaltet nach einer Minute den lokalen Alarm ein, bis jemand auf „Gesehen" tippt (siehe [So funktioniert es](how-it-works.md#die-drei-alarmstufen)). Die nächste Routinebewertung kann bis zum eingestellten Abstand entfernt sein; quittiere also selbst, nachdem du nachgesehen hast.

## Datenschutz und Einwilligung

- **Cloud oder lokal entscheidest du mit der KI-Aufgabe.** Bei einem Cloud-Anbieter wie Gemini oder OpenRouter verlässt mit jeder Bewertung ein Bild deines Kindes und seines Bettes dein Zuhause. Bei einem lokalen Modell, zum Beispiel über Ollama auf deinem eigenen Rechner, bleibt es in deinem Netz.
- **Die Einwilligung ist Pflicht.** KI-Aufgaben lassen sich ohne das Häkchen nicht speichern, und ohne das Häkchen wird kein Bild gesendet.
- **Prüfe die Bedingungen deines Anbieters.** Je nach Tarif kann ein Anbieter eingesandte Bilder zum Training seiner Modelle verwenden. Prüfe bei Gemini, ob du einen bezahlten Tarif nutzt und was er dazu sagt.
- **CheckBaby speichert keine Bilder.** Es behält die letzte Antwort im Arbeitsspeicher (die Felder und den einen Satz) und zeigt sie in den Sensoren „KI-Bewertung" und „Lage". Der Satz erscheint in Benachrichtigungen. Das geplante Fehlersuch-Archiv für Bilder ist nicht umgesetzt.
- **Home Assistant kann den Satz in seinem Verlauf behalten**, weil er ein Attribut des Sensors „KI-Bewertung" ist.
- **Der Privatmodus hält die automatischen Bewertungen an**, nicht die von Hand.

Siehe auch [Sicherheit und Datenschutz](safety-and-privacy.md).

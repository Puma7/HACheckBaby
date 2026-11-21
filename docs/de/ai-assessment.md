# KI-Bewertung

[English version](../en/ai-assessment.md) · [Zurück zur Übersicht](README.md)

Die KI-Bewertung ist optional. Sie schaut auf ein Standbild des Bettes und beantwortet eine feste Liste von Fragen: Ist das Kind da, wie liegt es, ist das Gesicht frei, liegen lose Gegenstände im Bett. Alles andere, auch jeder Wein-Alarm und die Ausfallüberwachung, funktioniert ohne sie und ohne Internet.

**Was geprüft ist und was nicht.** Der Aufrufweg ist im Labor des Projekts mit einem Modell geprüft, das nach Drehbuch antwortet: CheckBaby ruft die echte Aktion `ai_task` von Home Assistant auf, und das Kamerabild kommt als JPEG-Datei beim Modell an. Ein echter Anbieter (Google Gemini, OpenRouter, Ollama) wurde noch nicht ausprobiert. Ob jeder von ihnen den Bildanhang annimmt und wie gut ein Modell ein Infrarot-Nachtbild beurteilt, ist noch offen. Prüfe das Ergebnis mit einer Puppe, bevor du ihm Gewicht gibst.

## Wofür die KI nicht verwendet wird

**Die KI prüft nicht die Atmung.** Ein Sprach- und Bildmodell sieht einzelne Standbilder, braucht Sekunden für eine Antwort und kann überzeugend falsch liegen. Atmung ist eine winzige periodische Bewegung, für die es ein durchgehendes Signal braucht. Der [Atembewegungs-Hinweis](vital-sources.md) kommt deshalb von einem Radarsensor oder der Vital-Engine, nie von der KI. Wird „keine Atembewegung" erkannt, bittet CheckBaby die KI zwar um einen Blick als zusätzliche Information. Was auch immer die KI antwortet, kann diesen Alarm aber weder löschen noch herabstufen.

Der Eindruck der KI, ob das Kind schläft oder weint, wird mit der Antwort gespeichert und nicht verwendet. Der Zustand des Kindes kommt aus Frigate und deinen Sensoren.

## Was eine KI-Aufgabe ist und woher sie kommt

Eine „KI-Aufgabe" (englisch „AI Task") ist der Anschluss von Home Assistant an ein KI-Modell. CheckBaby spricht nicht selbst mit einem KI-Anbieter und fragt nie nach einem API-Schlüssel. Es übergibt das Kamerabild an eine KI-Aufgabe, und Home Assistant reicht es an das Modell weiter.

Eine KI-Aufgabe erscheint in der Liste von CheckBaby, sobald du in Home Assistant unter **Einstellungen → Geräte & Dienste** eine KI-Integration hinzugefügt hast, zum Beispiel Google Gemini, OpenRouter oder Ollama (für ein lokales Modell). Sie heißt meist wie der Anbieter. **Ist die Liste in CheckBaby leer, ist noch keine solche Integration eingerichtet.**

## Einrichten

1. **Füge die KI-Integration zu Home Assistant hinzu.** Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**, wähle **Google Gemini** oder **OpenRouter** und trage dort den API-Schlüssel ein. Ein lokales Modell über **Ollama** fügst du genauso hinzu. Das ist der eine Schritt, der außerhalb von CheckBaby geschieht.
2. **Öffne die Optionen von CheckBaby:** **Einstellungen → Geräte & Dienste → CheckBaby → Konfigurieren → KI-Bewertung**. Wenn du CheckBaby zum ersten Mal einrichtest, erscheint dieselbe Seite als „KI-Bewertung (optional)".
3. **Wähle das Modell** im Feld „KI-Modell (eine „KI-Aufgabe" von Home Assistant)".
4. **Bestätige, dass Bilder gesendet werden dürfen:** Kreuze „Bilder des Kindes dürfen an diese KI-Aufgaben gesendet werden" an. Ohne das Häkchen lässt sich die Seite nicht speichern, solange ein Modell gewählt ist.
5. **Drücke „KI-Check jetzt"** auf der Geräteseite und lies das Ergebnis in den Benachrichtigungen von Home Assistant (die Glocke in der Seitenleiste). Siehe [Das Ergebnis von „KI-Check jetzt"](#das-ergebnis-von-ki-check-jetzt).

Das ist alles. Die Bewertung läuft jetzt von selbst, sobald die Überwachung an ist. Du brauchst weder die Entwicklerwerkzeuge noch eine Automation noch YAML.

Gut zu wissen:

- Der Schlafplatz braucht eine **Kamera-Entität**. Von ihr stammt das Bild.
- Wählst du mehrere KI-Aufgaben, werden sie in dieser Reihenfolge gefragt, und die erste verwertbare Antwort gilt.
- **KI-Aufrufe pro Stunde höchstens** (1 bis 120, Standard 30) steht auf derselben Seite der Optionen.
- Der Schalter **KI-Bewertung** am Gerät ist standardmäßig an. Er ist eine Pausentaste: Schalte ihn aus, um die automatischen Bewertungen eine Zeit lang anzuhalten, ohne die KI-Aufgabe zu entfernen.

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

Automatische Bewertungen brauchen all das: eine KI-Aufgabe und die Einwilligung (aus der Einrichtung oder den Optionen), eine Kamera-Entität, Überwachung an, Privatmodus aus, der Schalter „KI-Bewertung" ist nicht ausgeschaltet, und das Kind ist nicht „Betreut".

| Auslöser | Wann |
|---|---|
| Zustandswechsel | Der Zustand wird „Weint" oder „Wach". |
| Keine Atembewegung | Die Regel für die Atembewegung beginnt zu gelten, auch im Schattenmodus. |
| Routine | Alle 10 Minuten (Zahl „Abstand der KI-Routineprüfung", 2 bis 60 Minuten), gezählt ab der letzten automatischen Bewertung. |
| Zweiter Blick | 15 Sekunden nach einer Bewertung, die eine Atemwegs- oder Bauchlage-Warnung oder ein erstes „Kamerablick verdeckt" ergeben hat. Nur einmal; ein zweiter Blick plant nie einen dritten. |
| Von Hand | Die Taste „KI-Check jetzt", die Aktion `checkbaby.assess_now` oder `checkbaby.quick_check` mit `with_ai`. |

Es läuft immer nur eine Bewertung gleichzeitig.

Eine Bewertung von Hand wird ausgeführt, sobald KI-Aufgaben, Einwilligung und eine Kamera-Entität eingerichtet sind und der Privatmodus aus ist. Sie beachtet weder den Schalter „KI-Bewertung" noch das Budget oder die Frage, ob die Überwachung an ist. Solange die Überwachung aus ist, wird ihr Ergebnis angezeigt, löst aber keinen Alarm aus.

**Im Privatmodus wird gar keine Bewertung ausgeführt, auch keine von Hand.** Es wird kein Bild gesendet; die Taste meldet nur, dass der Privatmodus an ist, und die Aktion gibt ein leeres Ergebnis zurück.

### Das Ergebnis von „KI-Check jetzt"

Die Taste „KI-Check jetzt" zeigt immer, was dabei herausgekommen ist: in den Benachrichtigungen von Home Assistant (die Glocke in der Seitenleiste) und als Benachrichtigung auf dem Handy im Dienst. Ein neueres Ergebnis ersetzt das ältere.

- **Lief ein Check,** liest du das Urteil der KI, wie sicher sie ist, und ihre Begründung in einem Satz, zum Beispiel „Sieht gut aus (90 % sicher). Das Kind liegt auf dem Rücken, und das Gesicht ist frei." Die Urteile heißen „Sieht gut aus", „Einen Blick wert", „Bitte nachsehen" und „Mögliche Gefahr".
- **Lief kein Check,** liest du den Grund: Es ist keine KI-Aufgabe gewählt, das Senden von Bildern ist nicht bestätigt, der Privatmodus ist an, der aktive Schlafplatz hat keine Kamera-Entität, oder es läuft schon ein Check.
- **Gab die KI keine brauchbare Antwort,** liest du das zusammen mit dem Fehler der zuletzt versuchten KI-Aufgabe: eine Zeitüberschreitung, die Fehlermeldung des Anbieters oder „unusable answer" (unbrauchbare Antwort).

Die Aktion `checkbaby.assess_now` verhält sich wie bisher: Sie gibt die Daten zurück und zeigt nichts an.

## Budget, Zeitlimit und Ausweichkette

- **Budget:** höchstens die eingestellte Zahl von Aufrufen in beliebigen 60 Minuten. Ist es verbraucht, entfallen automatische Bewertungen, bis Aufrufe aus der Stunde herausfallen. Bewertungen von Hand werden immer ausgeführt und zählen zum Budget. Der Sensor „KI-Aufrufe in der letzten Stunde" zeigt den Stand. Bei einer Routineprüfung alle 10 Minuten kannst du mit etwa 6 Aufrufen pro Stunde rechnen, dazu die ereignisgesteuerten; die Kosten hängen von deinem Anbieter ab.
- **Ausweichkette:** Die KI-Aufgaben werden in der Reihenfolge gefragt, die du gewählt hast. Die erste verwertbare Antwort gilt. So setzt du ein Cloud-Modell an die erste und ein lokales an die zweite Stelle, oder umgekehrt.
- **Zeitlimit:** Jede KI-Aufgabe hat 20 Sekunden. Eine Zeitüberschreitung, ein Fehler oder eine unbrauchbare Antwort führt zur nächsten Aufgabe.
- **Wenn keine antwortet:** Der Binärsensor „KI-Bewertung verfügbar" geht aus, und sonst ändert sich nichts. Ein Check, den du mit der Taste „KI-Check jetzt" gestartet hast, sagt das auch in seinem Ergebnis. Die deterministischen Alarme arbeiten wie zuvor. Eine KI, die nicht erreichbar ist, führt nie zu „alles in Ordnung".

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

Ein KI-Alarm endet, wenn eine spätere Bewertung seine Ursache nicht mehr meldet, und er sinkt auf eine niedrigere Stufe, wenn eine spätere Bewertung die Ursache als weniger ernst meldet. Ein sicheres „possible" nach einem „likely" zum Beispiel stuft eine Atemwegs-Warnung zum Hinweis herab, und die Benachrichtigung wird dann von den Handys entfernt. Eine Ausnahme schützt vor einem unsicheren Blick: Eine Bewertung, die nicht sicher ist, beendet einen KI-Alarm auf Stufe Warnung oder höher nicht und stuft ihn auch nicht herab. Die KI-Alarme werden außerdem gelöscht, wenn die Überwachung ausgeschaltet, der Privatmodus eingeschaltet wird oder jemand beim Kind ist.

Einmal ausgelöst, verhält sich ein KI-Alarm wie jeder andere Alarm seiner Stufe: Ein kritischer geht an alle Handys, wiederholt sich alle 30 Sekunden und schaltet nach einer Minute den lokalen Alarm ein, bis jemand auf „Gesehen" tippt (siehe [So funktioniert es](how-it-works.md#die-drei-alarmstufen)). Die nächste Routinebewertung kann bis zum eingestellten Abstand entfernt sein; quittiere also selbst, nachdem du nachgesehen hast.

## Datenschutz und Einwilligung

- **Cloud oder lokal entscheidest du mit der KI-Aufgabe.** Bei einem Cloud-Anbieter wie Gemini oder OpenRouter verlässt mit jeder Bewertung ein Bild deines Kindes und seines Bettes dein Zuhause. Bei einem lokalen Modell, zum Beispiel über Ollama auf deinem eigenen Rechner, bleibt es in deinem Netz.
- **Die Einwilligung ist Pflicht.** KI-Aufgaben lassen sich ohne das Häkchen nicht speichern, und ohne das Häkchen wird kein Bild gesendet.
- **Prüfe die Bedingungen deines Anbieters.** Je nach Tarif kann ein Anbieter eingesandte Bilder zum Training seiner Modelle verwenden. Prüfe bei Gemini, ob du einen bezahlten Tarif nutzt und was er dazu sagt.
- **CheckBaby speichert keine Bilder.** Es behält die letzte Antwort im Arbeitsspeicher (die Felder und den einen Satz) und zeigt sie in den Sensoren „KI-Bewertung" und „Lage". Der Satz erscheint in Benachrichtigungen. Das geplante Fehlersuch-Archiv für Bilder ist nicht umgesetzt.
- **Home Assistant kann den Satz in seinem Verlauf behalten**, weil er ein Attribut des Sensors „KI-Bewertung" ist.
- **Der Privatmodus hält jede Bewertung an**, die automatischen und die von Hand. Solange er an ist, wird kein Bild an eine KI-Aufgabe gesendet.

Siehe auch [Sicherheit und Datenschutz](safety-and-privacy.md).

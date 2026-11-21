# Entitäten und Aktionen

[English version](../en/entities-and-actions.md) · [Zurück zur Übersicht](README.md)

Jedes Kind ist ein Gerät. Alle Entitäten unten gehören dazu. Die Entitäts-IDs in den Tabellen sind die eines Kindes mit dem Namen „baby" auf einem Home Assistant mit deutscher Spracheinstellung.

## Entitäts-IDs hängen von der Sprache ab

Home Assistant bildet eine Entitäts-ID aus dem Gerätenamen und dem Namen der Entität, wenn die Entität zum ersten Mal angelegt wird. Ein Kind namens „Emma" bekommt `sensor.emma_zustand`.

Der Name der Entität wird in der Sprache genommen, die in diesem Moment unter **Einstellungen → System → Allgemein** eingestellt ist. Umlaute verlieren dabei ihre Punkte: Aus „Geräuschpegel" wird `gerauschpegel`, aus „Überwachung" wird `uberwachung`. Auf einem englisch eingestellten Home Assistant entsteht derselbe Sensor als `sensor.emma_state`. Die englischen IDs stehen in der [englischen Fassung dieser Seite](../en/entities-and-actions.md). IDs ändern sich nicht, wenn du die Sprache später umstellst; du kannst sie in den Einstellungen der Entität von Hand umbenennen.

Prüfe in Automationen und Dashboards die echten IDs auf der Geräteseite, bevor du ein Beispiel übernimmst.

Die Zustandswerte in Klammern (zum Beispiel `asleep`) sind in jeder Sprache gleich. Sie sind das, was du in Automationen und Vorlagen vergleichst; die Oberfläche zeigt die deutschen Bezeichnungen.

## Sensoren

| Name | Entitäts-ID | Bedeutung |
|---|---|---|
| Zustand | `sensor.baby_zustand` | Der Zustand des Kindes: `empty` (Nicht im Bett), `asleep` (Schläft), `restless` (Unruhig), `awake` (Wach), `crying` (Weint), `attended` (Betreut), `unknown` (Unbekannt). Attribut `since`: seit wann der Zustand gilt. |
| Alarmstufe | `sensor.baby_alarmstufe` | Höchste Stufe unter den aktiven Alarmen: `none` (Keine), `info` (Hinweis), `warning` (Warnung), `critical` (Kritisch). Attribut `alerts`: jeder aktive Alarm mit `kind`, `level`, `acknowledged`, `shadow` und `since`. Alarme, die nur aufgezeichnet werden (`shadow: true`), erscheinen hier und sonst nirgends. |
| Alarmgrund | `sensor.baby_alarmgrund` | Welcher Alarm die Stufe bestimmt, oder `none`. Die Attribute tragen die Einzelheiten dieses Alarms, zum Beispiel `seconds`, `problems`, `sources`, `reason`, `hazards` oder `temperature`. |
| Geräuschpegel | `sensor.baby_gerauschpegel` | Letzter Geräuschpegel in dBFS. |
| Gelernter Grundpegel | `sensor.baby_gelernter_grundpegel` | Diagnose. Der gelernte Pegel des Raums in dBFS. |
| Letzte Bewegung | `sensor.baby_letzte_bewegung` | Zeitpunkt der letzten gemeldeten Bewegung. |
| Schläft seit | `sensor.baby_schlaft_seit` | Beginn des laufenden Schlafs. Der Schlaf endet, wenn der Zustand „Wach", „Weint", „Betreut" oder „Nicht im Bett" wird; er läuft weiter, solange der Zustand „Unbekannt" ist. Schlafzeiten enthalten deshalb auch Strecken ohne brauchbares Signal. |
| Letzter Schlaf | `sensor.baby_letzter_schlaf` | Dauer des letzten abgeschlossenen Schlafs in Minuten. |
| Schlaf heute | `sensor.baby_schlaf_heute` | Stunden Schlaf seit Mitternacht. |
| Weinen heute | `sensor.baby_weinen_heute` | Minuten im Zustand „Weint" seit Mitternacht. |
| Aufgewacht heute Nacht | `sensor.baby_aufgewacht_heute_nacht` | Wie oft das Kind seit dem letzten 18:00 Uhr von schlafend oder unruhig auf wach oder weinend gewechselt ist. |
| Atemrate (Schätzung) | `sensor.baby_atemrate_schatzung` | Atemzüge pro Minute, wie sie eine Vitalquelle meldet, die gerade Atembewegung sieht. Eine Schätzung aus einer nicht validierten Quelle, keine Messung. |
| Herzrate (Schätzung) | `sensor.baby_herzrate_schatzung` | Der Wert des eingerichteten Herzraten-Sensors. Nur Anzeige; er löst nie einen Alarm aus. |
| Schlafsack-Empfehlung | `sensor.baby_schlafsack_empfehlung` | Ein TOG-Wert zur aktuellen Raumtemperatur nach den üblichen Herstellerangaben: unter 16 °C 3,5 TOG, unter 18 °C 2,5 TOG plus eine Schicht, unter 21 °C 2,5 TOG, unter 24 °C 1,0 TOG, unter 27 °C 0,5 TOG, darüber 0,2 TOG oder weniger. Eine Orientierung, keine Regel. |
| KI-Bewertung | `sensor.baby_ki_bewertung` | Gesamturteil der letzten KI-Bewertung: `ok`, `attention`, `warning`, `critical`. Attribute: `reason`, `position`, `airway_risk`, `face_visible`, `hazards`, `confidence`, `assessed_at`. Das Urteil wird nur angezeigt; Alarme folgen aus den einzelnen Feldern. |
| Lage | `sensor.baby_lage` | Körperlage aus der letzten KI-Bewertung: `supine` (Rückenlage), `prone` (Bauchlage), `side` (Seitenlage), `sitting`, `standing`, `unknown`. |
| Störungen der Überwachung | `sensor.baby_storungen_der_uberwachung` | Diagnose. Anzahl der Störungen. Attribut `problems`: ihre Namen. |
| KI-Aufrufe in der letzten Stunde | `sensor.baby_ki_aufrufe_in_der_letzten_stunde` | Diagnose. Wie viel vom stündlichen KI-Budget verbraucht ist. |
| Altersprofil | `sensor.baby_altersprofil` | Diagnose. `newborn` (Neugeborenes), `infant` (Säugling) oder `toddler` (Kleinkind), aus dem Geburtsdatum. |

## Binärsensoren

| Name | Entitäts-ID | Bedeutung |
|---|---|---|
| Weinen | `binary_sensor.baby_weinen` | Gerade ist Weinen oder Schreien zu hören, noch bevor eine Dauer angewendet wird. |
| Bewegung | `binary_sensor.baby_bewegung` | Gerade wird Bewegung gemeldet. |
| Im Bett | `binary_sensor.baby_im_bett` | Der Präsenzsensor des Bettes. Unbekannt, wenn keiner eingerichtet ist. |
| Jemand ist beim Kind | `binary_sensor.baby_jemand_ist_beim_kind` | An, solange der Zustand „Betreut" ist. |
| Atembewegung | `binary_sensor.baby_atembewegung` | An, solange eine brauchbare Vitalquelle Atembewegung sieht; aus, solange die brauchbaren Quellen keine sehen; **unbekannt, solange keine Quelle brauchbar ist**. Unbekannt heißt nicht „alles in Ordnung". |
| Unbeantworteter Alarm | `binary_sensor.baby_unbeantworteter_alarm` | An, solange eine Warnung oder ein kritischer Alarm nicht quittiert ist. |
| Störung der Überwachung | `binary_sensor.baby_storung_der_uberwachung` | Diagnose. An, solange mindestens eine Störung besteht. |
| KI-Bewertung verfügbar | `binary_sensor.baby_ki_bewertung_verfugbar` | Diagnose. An nach einer verwertbaren KI-Antwort, aus nach einem gescheiterten Versuch, unbekannt vor dem ersten Versuch. |
| Ruhezeit | `binary_sensor.baby_ruhezeit` | An, solange die Überwachung an, der Privatmodus aus und das Kind schlafend oder unruhig ist. Für eigene Automationen gedacht. |
| Ton-Weiterleitung läuft | `binary_sensor.baby_ton_weiterleitung_lauft` | An, solange die Ton-Weiterleitung den Stream auf dem Lautsprecher geöffnet hat. |

## Schalter

| Name | Entitäts-ID | Standard | Bedeutung |
|---|---|---|---|
| Überwachung | `switch.baby_uberwachung` | aus | Schaltet die Überwachung scharf. Solange sie aus ist, melden sich nur Rauch/CO und der Testalarm. |
| Privatmodus | `switch.baby_privatmodus` | aus | Pausiert Erkennung und Benachrichtigungen, siehe [So funktioniert es](how-it-works.md#privatmodus). |
| KI-Bewertung | `switch.baby_ki_bewertung` | aus | Erlaubt die automatischen KI-Bewertungen. Braucht KI-Aufgaben und Einwilligung in den Optionen. |
| Atembewegungs-Alarm | `switch.baby_atembewegungs_alarm` | aus | Aus: „keine Atembewegung" wird nur aufgezeichnet (Schattenmodus). An: Es löst einen kritischen Alarm aus. Lies [Vitalquellen](vital-sources.md), bevor du ihn einschaltest. |
| Ton-Weiterleitung | `switch.baby_ton_weiterleitung` | aus | Spielt den Ton-Stream des Zimmers auf dem Lautsprecher, solange es Geräusch gibt. |

## Zahlen

| Name | Entitäts-ID | Bereich | Standard | Bedeutung |
|---|---|---|---|---|
| Weinen bis zur Warnung | `number.baby_weinen_bis_zur_warnung` | 5 bis 120 s | 15 s | Ununterbrochenes Weinen bis zur Warnung. Skaliert durch Empfindlichkeit und Babysitter-Modus. |
| Unbeantwortetes Weinen bis kritisch | `number.baby_unbeantwortetes_weinen_bis_kritisch` | 60 bis 900 s | 180 s | Wie lange eine Wein-Warnung unquittiert bleiben darf, bevor sie kritisch wird. |
| Lautstärke über dem Grundpegel | `number.baby_lautstarke_uber_dem_grundpegel` | 3 bis 40 dB | 15 dB | Wie weit ein Pegel über dem gelernten Grundpegel liegen muss, um als Geräusch zu zählen. |
| Keine Atembewegung bis zum Alarm | `number.baby_keine_atembewegung_bis_zum_alarm` | 20 bis 60 s | 20 s | Lässt sich nicht unter 20 Sekunden stellen, siehe [Vitalquellen](vital-sources.md#warum-20-sekunden-die-untergrenze-sind). |
| Abstand der KI-Routineprüfung | `number.baby_abstand_der_ki_routineprufung` | 2 bis 60 min | 10 min | Zeit zwischen den routinemäßigen KI-Bewertungen. |
| Niedrigste Raumtemperatur | `number.baby_niedrigste_raumtemperatur` | 10 bis 22 °C | 16 °C | Unteres Ende des Bereichs für den Raumklima-Alarm. |
| Höchste Raumtemperatur | `number.baby_hochste_raumtemperatur` | 18 bis 30 °C | 22 °C | Oberes Ende des Bereichs. |

## Auswahlen

| Name | Entitäts-ID | Optionen | Bedeutung |
|---|---|---|---|
| Modus | `select.baby_modus` | `night` (Nacht), `nap` (Nickerchen), `babysitter` | Siehe [So funktioniert es](how-it-works.md#modi-und-empfindlichkeit). |
| Empfindlichkeit | `select.baby_empfindlichkeit` | `low` (Niedrig), `medium` (Mittel), `high` (Hoch) | Verdoppelt, belässt oder halbiert die Wein-Dauer bis zur Warnung. |
| Vitalquellen müssen übereinstimmen | `select.baby_vitalquellen_mussen_ubereinstimmen` | `any` (Eine Quelle genügt), `all` (Alle Quellen) | Wie mehrere Vitalquellen zusammenwirken. Standard `all`. |
| Hat Dienst | `select.baby_hat_dienst` | `all` (Alle) und jedes eingerichtete Handy | Wer Warnungen zuerst bekommt. |
| Aktiver Schlafplatz | `select.baby_aktiver_schlafplatz` | Die Namen deiner Schlafplätze | Welcher Schlafplatz überwacht wird. |

## Tasten

| Name | Entitäts-ID | Was sie tut |
|---|---|---|
| Gesehen | `button.baby_gesehen` | Quittiert alle aktiven Alarme. |
| 5 Minuten Ruhe | `button.baby_5_minuten_ruhe` | Hält Warnungen fünf Minuten zurück. |
| Schnell-Check | `button.baby_schnell_check` | Sendet eine Zusammenfassung in ein oder zwei Sätzen an das Handy im Dienst. |
| KI-Check jetzt | `button.baby_ki_check_jetzt` | Fragt die KI zu einem frischen Kamerabild, unabhängig vom Schalter „KI-Bewertung", vom Budget und vom Privatmodus. |
| Nachtbericht senden | `button.baby_nachtbericht_senden` | Sendet den Nachtbericht an das Handy im Dienst. |
| Testalarm | `button.baby_testalarm` | Diagnose. Startet einen kritischen Testalarm. |

## Ereignis

| Name | Entitäts-ID | Bedeutung |
|---|---|---|
| Alarm | `event.baby_alarm` | Löst aus, wenn ein Alarm zum ersten Mal eine Benachrichtigung sendet und wenn er auf eine höhere Stufe steigt. Der Ereignistyp ist der Alarmgrund: `crying`, `no_breathing`, `airway_risk`, `prone_position`, `hazard`, `camera_view`, `left_bed`, `pet_in_bed`, `climate`, `smoke`, `monitoring_failure`, `internet_down`, `interruption`, `test`. Das Attribut `level` ist `warning` oder `critical`; die Einzelheiten des Alarms sind weitere Attribute. |

Das Ereignis löst nicht aus bei Hinweisen, bei Wiederholungen, bei der Wiederholung an alle Handys nach 180 Sekunden und bei Alarmen, die nur aufgezeichnet werden. Eine Warnung, die durch Schlummern zurückgehalten wird, löst aus, wenn sie nach der Ruhezeit gesendet wird.

## Aktionen

Jede Aktion nimmt das optionale Feld `config_entry_id` an (angezeigt als „Kind"). Du brauchst es nur, wenn mehr als ein Kind eingerichtet ist; bei genau einem Kind kannst du es weglassen. Fehlt es bei mehreren Kindern, scheitert die Aktion mit „Bitte das Kind wählen".

| Aktion | Felder | Was sie tut | Rückgabe |
|---|---|---|---|
| `checkbaby.acknowledge` | – | Markiert alle aktiven Warnungen und kritischen Alarme als gesehen. | Nichts |
| `checkbaby.snooze` | `minutes` (1 bis 120, Standard 5) | Hält Warnungen so lange zurück. Kritische Alarme kommen trotzdem durch. | Nichts |
| `checkbaby.test_alert` | `level`: `critical` (Standard) oder `warning` | Durchläuft die Benachrichtigungskette mit einem Testalarm, bis quittiert wird, höchstens 10 Minuten. Funktioniert auch bei ausgeschalteter Überwachung. | Nichts |
| `checkbaby.start_sleep` | – | Setzt den Zustand jetzt auf „Schläft". | Nichts |
| `checkbaby.end_sleep` | – | Setzt den Zustand jetzt auf „Wach". | Nichts |
| `checkbaby.assess_now` | – | Fragt die eingerichteten KI-Aufgaben zu einem frischen Kamerabild. | `assessment` |
| `checkbaby.quick_check` | `with_ai` (Standard false): zuerst einen frischen KI-Blick einholen. `notify` (Standard false): die Zusammenfassung zusätzlich an das Handy im Dienst senden. | Meldet, wie es dem Kind gerade geht. | Siehe unten |
| `checkbaby.night_report` | `notify` (Standard false) | Meldet die Nacht seit dem letzten 18:00 Uhr. | Siehe unten |

### Was `assess_now` zurückgibt

`assessment` ist leer (`null`), wenn keine KI-Aufgabe eingerichtet ist, die Einwilligung fehlt, der Schlafplatz keine Kamera-Entität hat, gerade eine andere Bewertung läuft oder keine KI-Aufgabe eine verwertbare Antwort gegeben hat. Sonst enthält es:

| Schlüssel | Wert |
|---|---|
| `presence` | `in_bed`, `not_visible` oder `caregiver_present` |
| `position` | `supine`, `prone`, `side`, `sitting`, `standing`, `unknown` |
| `face_visible` | true, false oder leer |
| `airway_risk` | `none`, `possible`, `likely` |
| `state` | `asleep`, `awake_calm`, `awake_restless`, `crying`, `unknown` |
| `view_ok` | false, wenn das Bild zu dunkel oder verdeckt ist oder kein Bett zeigt |
| `verdict` | `ok`, `attention`, `warning`, `critical` |
| `confidence` | 0 bis 1 |
| `reason` | Ein Satz in der Sprache deines Home Assistant |
| `hazards` | Liste der losen Gegenstände, die die KI genannt hat |
| `at` | Zeitpunkt der Bewertung als Unix-Zeitstempel |

### Was `quick_check` zurückgibt

| Schlüssel | Wert |
|---|---|
| `state` | Der Zustand wie im Sensor, zum Beispiel `asleep` |
| `state_text` | Der Zustand in Worten, in der Sprache deines Home Assistant |
| `alert_level` | `none`, `info`, `warning`, `critical` |
| `alert` | Der Alarmgrund, oder leer |
| `asleep_minutes` | Minuten seit Beginn des laufenden Schlafs, oder leer |
| `noise_level` | Letzter Geräuschpegel in dBFS, oder leer |
| `breathing_movement` | true, false, oder leer, wenn keine Vitalquelle brauchbar ist |
| `problems` | Liste der Störungen der Überwachung |
| `assessment`, `assessment_reason` | Urteil und Satz der letzten KI-Bewertung, oder leer |
| `summary` | Ein oder zwei Sätze, zum Beispiel „baby: schläft. Schläft seit 42 min." |

Einen eingebauten Sprachbefehl „Wie geht es dem Baby?" gibt es nicht. Du kannst `checkbaby.quick_check` aus einem Skript aufrufen und deinen Sprachassistenten `summary` vorlesen lassen.

### Was `night_report` zurückgibt

| Schlüssel | Wert |
|---|---|
| `since`, `until` | Beginn (das letzte 18:00 Uhr) und Ende (jetzt) als Unix-Zeitstempel |
| `slept_seconds` | Sekunden Schlaf in dieser Zeit |
| `cried_seconds` | Sekunden im Zustand „Weint" |
| `wakeups` | Anzahl der Aufwachphasen |
| `sleep_phases` | Anzahl getrennter Schlafphasen |
| `longest_stretch_seconds` | Längste Schlafphase in Sekunden |
| `summary` | Ein Satz mit diesen Zahlen |

Ein neuer Schlaf, der weniger als 20 Minuten nach dem Ende des letzten beginnt, zählt als Fortsetzung derselben Schlafphase.

### Beispiel: einen Rückgabewert verwenden

```yaml
action: checkbaby.quick_check
data:
  with_ai: false
response_variable: check
```

Nach diesem Schritt enthält `{{ check.summary }}` den Satz.

## Diagnose

**Diagnose herunterladen** am Eintrag liefert dir die Einstellungen, die Schlafplätze, den letzten Stand und die letzten 300 Einträge des Ereignisprotokolls, das jeden Zustandswechsel, jeden Alarm, jede Quittierung und jede KI-Antwort mit ihrer Ursache festhält. Der Name des Kindes, das Geburtsdatum, die Adresse des Ton-Streams, die Namen der Schlafplätze und die Sätze der KI werden entfernt. Die Namen deiner Benachrichtigungsdienste und Entitäten sind enthalten.

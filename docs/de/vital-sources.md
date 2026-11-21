# Vitalquellen: der Atembewegungs-Hinweis

[English version](../en/vital-sources.md) · [Zurück zur Übersicht](README.md)

CheckBaby kann Quellen einbinden, die melden, ob sie Atembewegung sehen, und einen Alarm auslösen, wenn eine Quelle, die vorher Bewegung gesehen hat, eine Zeit lang keine mehr sieht. Das ist ein **Atembewegungs-Hinweis**. Es ist keine medizinische Messung.

> **An Säuglingen ist das nicht validiert.** Nichts auf dieser Seite lief bisher an echter Hardware, und kein Radarmodul auf dem Markt ist für Säuglinge ausgelegt. Die Regel ist durch automatische Tests mit simulierten Messwerten abgedeckt; niemand hat bisher gemessen, wie oft sie eine echte Pause übersieht oder einen Fehlalarm auslöst. Für kein Überwachungsgerät ist belegt, dass es den plötzlichen Kindstod verhindert. Verlass dich nicht auf den Hinweis, lass ihn nicht das Nachsehen bei deinem Kind ersetzen, und halte dich weiter an die [Regeln für sicheren Schlaf](safety-and-privacy.md#grundregeln-für-sicheren-schlaf).

Der Alarm ist ausgeschaltet, wenn du CheckBaby installierst. In diesem Zustand läuft die Regel im **Schattenmodus**: Sie zeichnet auf, sagt aber niemandem Bescheid. Lass das so, bis du dir ihre Aufzeichnungen mindestens zwei Wochen lang angesehen hast.

## Die zwei Arten von Quellen

Ein Schlafplatz kann von jeder Art eine haben. Beide lassen sich zusammen nutzen.

### Ein Radarsensor (Atemraten-Entität)

Trage im Schlafplatz unter **Atemraten-Sensor (Radar)** einen Sensor ein. CheckBaby liest seinen Zustand alle zwei Sekunden und deutet ihn so:

| Zustand der Entität | Bedeutung für CheckBaby |
|---|---|
| Eine Zahl ungleich null | Brauchbar, Atembewegung gesehen. Die Zahl wird als „Atemrate (Schätzung)" angezeigt. |
| Null | Brauchbar, keine Atembewegung gesehen. |
| `unavailable`, `unknown`, keine Zahl, oder die Entität fehlt | Nicht brauchbar. Die Ausfallüberwachung meldet `vital_sensor`. |
| Jeder Wert, den der Sensor seit 120 Sekunden nicht erneut gemeldet hat | Nicht brauchbar, wie oben. Ein Sensor, der ausgefallen ist, während er eine Rate anzeigte, sähe sonst aus wie einer, der sie noch misst. |

In die Regel geht nur die Unterscheidung „null oder nicht" ein. Die Rate selbst wird angezeigt und nicht bewertet, weil noch niemand weiß, ob ein für Erwachsene gebautes Modul bei einem Neugeborenen plausible Raten meldet.

Die 120 Sekunden zählen ab der letzten Meldung des Sensors, auch wenn er denselben Wert noch einmal gemeldet hat. Ein Sensor, der nur bei einer Änderung meldet und zwei Minuten lang eine gleichbleibende Rate hält, erscheint deshalb als Störung `vital_sensor`; dasselbe gilt für einen Filter in der Konfiguration des Sensors, der wiederholte Werte unterdrückt. „Atembewegung" ist in dieser Zeit unbekannt.

Hier passt jede Entität mit einer Atemrate als Zahl, gleich von welchem Hersteller. Eine Radarquelle meldet CheckBaby nie Körperbewegung; Bewegung kommt von der Kamera.

Das Feld **Herzraten-Sensor (Radar)** wird als „Herzrate (Schätzung)" angezeigt und löst nie einen Alarm aus. Die Herzbewegung eines Babys ist noch einmal deutlich kleiner als seine Atembewegung, und der Wert ist nicht gegen ein Referenzgerät geprüft.

### Die Vital-Engine

Die Vital-Engine ist ein eigenes Programm im Ordner `engine/` des Repositorys. Sie liest den niedrig aufgelösten Stream der Kamera, betrachtet einen Bildausschnitt über dem Oberkörper des Kindes und veröffentlicht, ob sie dort eine periodische Bewegung im Bereich der Atmung sieht. Sie läuft bewusst außerhalb von Home Assistant: Video in Home Assistant zu dekodieren, würde bei einem Fehler deine gesamte Hausautomation gefährden.

Ihre Signalverarbeitung wurde nur mit künstlichen Signalen getestet. Sie hat noch nie eine echte Kamera, einen echten Raum oder ein echtes Kind gesehen, und ihre Schwellen sind an künstlichen Daten eingestellt. Die Verpackung als Home-Assistant-Add-on ist ungetestet. Wie du sie startest, was genau getestet wurde und ihre eigene Liste von Grenzen stehen in [`engine/README.md`](../../engine/README.md) (englisch).

Trage im Schlafplatz unter **ID der Vital-Engine** die ID der Engine ein. CheckBaby abonniert dann zwei MQTT-Themen. Das Präfix `checkbaby/engine` ist in der Integration fest; lass `topic_prefix` der Engine also auf dem Standardwert.

| Thema | Nutzlast |
|---|---|
| `checkbaby/engine/<id>/availability` | `online` oder `offline` |
| `checkbaby/engine/<id>/state` | JSON, etwa alle zwei Sekunden, zum Beispiel `{"status": "periodic", "rate": 38.0, "confidence": 0.6, "motion": 0.4, "ts": 1800000000.0}` |

CheckBaby liest `status` und `rate` und ignoriert die übrigen Schlüssel:

| `status` | Bedeutung für CheckBaby |
|---|---|
| `periodic` | Brauchbar, Atembewegung gesehen; `rate` wird als geschätzte Rate angezeigt. |
| `gross_motion` | Brauchbar, das Kind bewegt sich. Die Atmung ist nicht messbar, aber es gibt ein Lebenszeichen. |
| `no_motion` | Brauchbar, weder periodische noch grobe Bewegung. |
| alles andere, zum Beispiel `unusable` | Nicht brauchbar: verdeckt, Kind nicht im Bild, zu dunkel, zu viel Bildrauschen. |

Kommt 15 Sekunden lang keine Zustandsmeldung, gilt der letzte Messwert nicht mehr als brauchbar. Nach 30 Sekunden, oder wenn die Engine `offline` meldet, meldet die Ausfallüberwachung `engine`.

Der Plan beschreibt diesen Vertrag mit deutschen Namen; die Namen oben sind die, die Engine und Integration wirklich verwenden.

## Die Regel

„Keine Atembewegung" gilt, wenn **alles** Folgende zutrifft:

1. Die Überwachung ist an und der Privatmodus aus.
2. Der Zustand ist weder „Betreut" noch „Nicht im Bett", und der Präsenzsensor meldet kein leeres Bett.
3. Die Kamera meldet keine Bewegung, und es ist weder Weinen noch Schreien zu hören. Jedes davon ist ein Lebenszeichen und schließt den Alarm aus.
4. Mindestens eine Vitalquelle ist gerade brauchbar.
5. Diese Quelle **hat vorher schon Atembewegung gesehen**. Eine Quelle, die das Kind nie atmen gesehen hat, kann nicht sagen, dass etwas aufgehört hat.
6. **Diese Quelle hat mindestens 10 Sekunden nach der letzten großen Bewegung Atembewegung gesehen.** Eine große Bewegung ist: Die Kamera meldet Bewegung (Frigates Bewegungserkennung oder dein Bewegungssensor; auch der Moment, in dem sie endet, zählt), oder eine Vitalquelle meldet Körperbewegung (`gross_motion` der Engine).
7. Seit sie zuletzt Atembewegung gesehen hat, und solange ihr Signal ohne Unterbrechung brauchbar ist, hat die Quelle für die eingestellte Zeit weder Atembewegung noch Körperbewegung gesehen (Zahl „Keine Atembewegung bis zum Alarm", 20 bis 60 Sekunden, Standard 20).

Der Alarm ist kritisch. Er endet, sobald eine Quelle wieder Bewegung sieht oder eine der Bedingungen nicht mehr zutrifft.

Solange der Zustand „Betreut" ist, vergisst jede Quelle, dass sie Atembewegung gesehen hat. Nachdem die Person gegangen ist, muss jede Quelle erst wieder Atembewegung sehen, bevor ihre Stille zählen kann.

### Stille nach einer großen Bewegung zählt nicht

Punkt 6 gibt es wegen des häufigsten Fehlalarms: Du hebst das Kind aus dem Bett. Das ist eine große Bewegung, auf die ein Bett folgt, in dem nichts atmet, und keine Quelle kann das von etwas Schlimmerem unterscheiden. CheckBaby zählt Stille nach einer großen Bewegung deshalb nie. Die Quelle muss erst wieder Atembewegung sehen.

**Der Preis, klar gesagt: Hört die Atembewegung direkt nach einer großen Bewegung auf, bevor die Quelle wieder Atmung gesehen hat, bemerkt der Hinweis das nicht.** Bei der Vital-Engine sind das mindestens die etwa 12 Sekunden, in denen sie nach jeder größeren Bewegung `gross_motion` meldet, dazu die Zeit, bis sie wieder `periodic` meldet. Ein Kind, das sich bewegt und dann still unter einem dicken Schlafsack liegt, sodass die Quelle nie wieder Atmung sieht, ist gar nicht abgedeckt, bis wieder Atmung gesehen wird.

### Was nie als „keine Bewegung" zählt

- Eine Quelle, die nicht verfügbar oder offline ist oder „unusable" meldet.
- Ein Messwert, der älter als 15 Sekunden ist.
- Eine Quelle, die das Kind noch nicht atmen gesehen hat.
- Stille nach einer großen Bewegung, bis die Quelle wieder Atembewegung gesehen hat.
- Stille, nachdem jemand beim Kind war, bis die Quelle wieder Atembewegung gesehen hat.
- Die Zeit, in der das Signal unbrauchbar war: Kommt ein Signal zurück, beginnt die Zählung in diesem Moment neu.

In all diesen Fällen bleibt die Regel still. Solange gar keine Quelle brauchbar ist, zeigt der Binärsensor „Atembewegung" **unbekannt**. Das ist Absicht: Ein unbrauchbares Signal ist ein sichtbarer Zustand, kein Alarm und nie „alles in Ordnung". Es heißt aber auch, dass der Hinweis über lange Strecken blind sein kann, ohne dass dich eine Benachrichtigung darauf hinweist. Schau auf den Sensor.

### Mehrere Quellen: „eine" oder „alle"

Die Auswahl **Vitalquellen müssen übereinstimmen** entscheidet, was bei zwei Quellen geschieht:

| Option | Die Regel gilt, wenn | Charakter |
|---|---|---|
| Alle Quellen (Standard) | jede gerade brauchbare Quelle keine Bewegung sieht | weniger Fehlalarme |
| Eine Quelle genügt | mindestens eine brauchbare Quelle keine Bewegung sieht | empfindlicher |

„Alle Quellen" heißt: alle *brauchbaren* Quellen. Eine Quelle, die in dem Moment unbrauchbar ist, hat keine Stimme: Ist das Radar nicht verfügbar und die Engine sieht keine Bewegung, gilt die Regel allein aufgrund der Engine.

### Schattenmodus

Der Schalter **Atembewegungs-Alarm** ist standardmäßig aus.

- **Aus:** Gilt die Regel, wird der Alarm nur aufgezeichnet. Keine Benachrichtigung, kein lokaler Alarm, keine Änderung der Alarmstufe. Du findest ihn im Attribut `alerts` des Sensors „Alarmstufe" mit `shadow: true`, solange er besteht, und danach im Ereignisprotokoll des Diagnose-Downloads. Ist die KI-Bewertung an, wird ein KI-Blick angefordert.
- **An:** Dieselbe Lage löst einen kritischen Alarm aus: alle Handys, Wiederholung alle 30 Sekunden, lokaler Alarm nach einer Minute.

Schaltest du den Alarm ein, während ein aufgezeichneter Alarm besteht, meldet er sich sofort. Schaltest du ihn aus, während er ertönt, wird die Benachrichtigung entfernt.

Ein sinnvoller Umgang mit dem Schattenmodus: mindestens 14 Nächte laufen lassen, jeden Morgen die Diagnose herunterladen oder den Sensor „Alarmstufe" mit seinen Attributen aufzeichnen, und zählen, wie oft die Regel galt, obwohl alles in Ordnung war. Ein Werkzeug zur Auswertung ist noch nicht gebaut.

### Warum 20 Sekunden die Untergrenze sind

Neugeborene atmen unregelmäßig. Pausen bis etwa zehn Sekunden gehören in den ersten Wochen zur normalen Atmung. Eine kürzere Zeit würde bei gesunden Kindern jede Nacht Alarme auslösen, und auf Alarme, die meist falsch sind, reagiert irgendwann niemand mehr. Die Zeit lässt sich deshalb nicht unter 20 Sekunden stellen.

## Bekannte Grenzen

- **Pucksack, Schlafsack und dicke Decken** verbergen die Bewegung vor einer Kamera.
- **Seitenlage mit dem Rücken zur Kamera**, ein flacher Kamerawinkel und Bildrauschen bei Infrarot schwächen das Videosignal.
- **Ein Ventilator oder ein Mobile im Bildausschnitt** der Engine erzeugt eine eigene periodische Bewegung.
- **Radarmodule sind für Erwachsene** bei bis zu 1,5 m ausgelegt. Ein Neugeborenes hat einen viel kleineren Brustkorb, atmet 30- bis 60-mal pro Minute und hat einen Puls von 100 bis 160. Ob die Firmware eines Moduls dafür plausible Werte liefert oder Bereiche abschneidet, steht in keiner Quelle und muss gemessen werden.
- **Ein Ende der Atembewegung direkt nach einer großen Bewegung wird nicht erkannt**, bis die Quelle wieder Atembewegung gesehen hat. Siehe [oben](#stille-nach-einer-großen-bewegung-zählt-nicht).
- **Ein leeres Bett sieht aus wie ein Kind, das sich nicht bewegt.** Ein Radar, das null meldet, und eine Engine, die `no_motion` meldet, sagen für beides dasselbe. Das Herausheben des Kindes löst den Alarm normalerweise nicht aus, weil es eine große Bewegung ist und weil die Quellen vergessen, was sie gesehen haben, solange jemand beim Kind ist. Dieser Schutz hat Lücken: Er braucht, dass die Bewegung gesehen wird (ein Schlafplatz nur mit Radar, ohne Kamerabewegung und ohne Türkontakt, hat kein solches Signal), und Atembewegung gilt erst dann als wieder gesehen, wenn eine Quelle sie mindestens 10 Sekunden nach der letzten großen Bewegung meldet, weil ein Radar seine letzte Rate noch ein paar Sekunden anzeigen kann, nachdem das Kind weg ist. Ein Radar, das einen veralteten Wert länger hält, kann die Regel trotzdem gelten lassen. Ein Präsenzsensor für das Bett bleibt der verlässliche Weg, CheckBaby zu sagen, dass das Bett leer ist. Was die Radarmodule bei leerem Bett tatsächlich melden und wie schnell, wurde nicht gemessen.
- **Eine Schwenkkamera, die bewegt wurde**, zeigt nicht mehr den Ausschnitt, für den die Engine eingerichtet wurde.
- **Ein Haustier in Bewegung, ein Vorhang oder der Arm eines Elternteils** kann als Lebenszeichen zählen.
- **Jede Quelle kann verspätet sein.** Die Regel legt ihre 20 Sekunden oder mehr auf die Verzögerung der Quelle obendrauf. Die Vital-Engine beurteilt ein Fenster von bis zu 25 Sekunden und meldet `no_motion` deshalb erst einige Zeit, nachdem die Atembewegung aufgehört hat: 18 bis 21 Sekunden in ihren Tests mit künstlichen Signalen. Über den Kameraweg liegt der Hinweis deshalb etwa 40 Sekunden oder mehr hinter dem Ereignis.
- **Die Vital-Engine meldet nur Raten zwischen 18 und 90 pro Minute** als Atembewegung, und nach jeder größeren Bewegung meldet sie etwa 12 Sekunden lang `gross_motion`, bevor sie wieder urteilen kann.

## Hinweise zur Hardware

### Seeed MR60BHA2

Ein 60-GHz-Radarmodul, als Kit mit einem XIAO ESP32-C6 erhältlich. Mit ESPHome meldet es Atemrate, Herzrate, Abstand und die Zahl der Ziele lokal, ohne Cloud. Eine Beispielkonfiguration liegt in [`esphome-mr60bha2.yaml`](../examples/esphome-mr60bha2.yaml); sie ist ungetestet.

- Trage seine Atemraten-Entität unter „Atemraten-Sensor (Radar)" und seine Herzraten-Entität unter „Herzraten-Sensor (Radar)" ein.
- Seine Ziel- oder Präsenz-Entität kann als „Präsenzsensor für das Bett" dienen, falls sie sich als verlässlich erweist.
- Geplant ist, zunächst nur die robuste Aussage „Ziel vorhanden und Atembewegung gesehen: ja oder nein" zu nutzen, nicht die exakte Rate. So behandelt es die Integration.
- Vor dem Einsatz am Kind: an einem Erwachsenen gegen eine Smartwatch oder ein Pulsoximeter testen, 20 Sekunden die Luft anhalten und notieren, was der Sensor meldet, und notieren, was er bei leerem Bett meldet.

### Aqara FP2

Der FP2 meldet Präsenz und Zonen lokal über HomeKit. Seine Atemrate, Herzrate und Schlafphase gibt es nur in der Aqara-Cloud; ein Community-Add-on (SleepRadar) liest sie von dort.

- Lokal ist er als **Präsenzsensor für das Bett** nützlich („liegt im Bett").
- Seine Vitaldaten über die Cloud sind bestenfalls experimentell: Sie hängen vom Internet ab, sind für Erwachsene ausgewertet, und ihre Verzögerung ist unbekannt. Nutze sie nicht als alleinigen Grund für einen Alarm.
- Ein Schlafplatz hat ein Feld für eine Atemraten-Entität. Du kannst MR60BHA2 und FP2 nicht als zwei Radarquellen desselben Schlafplatzes eintragen.
- Ob sich zwei 60-GHz-Sensoren am selben Bett gegenseitig stören, wurde nicht geprüft.

Andere Sensoren (Aqara FP300 und FP400) melden nur Präsenz und keine Vitaldaten. DFRobot C1001 und HLK-LD6002 melden Vitaldaten, brauchen aber eine eigene ESP32-Firmware; sie sind Alternativen, falls der MR60BHA2 nicht taugt.

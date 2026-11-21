# So funktioniert es

[English version](../en/how-it-works.md) · [Zurück zur Übersicht](README.md)

CheckBaby schaut alle zwei Sekunden auf seine Signale, und sofort, wenn sich eine beobachtete Entität ändert. Jedes Mal tut es drei Dinge: Es bestimmt den Zustand des Kindes, es entscheidet, welche Alarme aktiv sein sollen, und es entscheidet, wem jetzt Bescheid gegeben wird.

Alle Zeiten auf dieser Seite sind die Werte im Code. Die einstellbaren sind gekennzeichnet; die Entitäten dazu stehen in [Entitäten und Aktionen](entities-and-actions.md). Keine der Zeiten wurde bisher an einem echten Kind abgestimmt.

## Der Zustand des Kindes

Der Sensor **Zustand** hat sieben Werte. Ein Wechsel hängt immer davon ab, wie lange etwas schon dauert, nie an einem einzelnen Ereignis.

| Zustand | Bedeutung |
|---|---|
| Schläft | Im Bett und ruhig. |
| Unruhig | Seit einer Weile Bewegung oder Geräusch, aber noch nicht wach. |
| Wach | Wach oder gerade hingelegt, und weint nicht. |
| Weint | Weint oder schreit. |
| Betreut | Jemand ist beim Kind. Kindbezogene Alarme pausieren. |
| Nicht im Bett | Der Präsenzsensor meldet ein leeres Bett. |
| Unbekannt | CheckBaby kann es nicht sagen, weil eine Kernquelle ausgefallen oder der Privatmodus an ist. |

„Geräusch" heißt hier: Der Geräuschpegel liegt um mehr als den eingestellten Abstand (Standard 15 dB) über dem gelernten Grundpegel. „Ruhig" heißt: keine Bewegung und kein Geräusch.

Die Regeln werden in dieser Reihenfolge geprüft:

1. **Unbekannt**, wenn eine Kernquelle gestört ist (siehe [Ausfallüberwachung](#die-ausfallüberwachung)) oder der Privatmodus an ist. Ein fehlendes Signal wird nie als „Schläft" angezeigt.
2. **Betreut**, solange der Türkontakt offen ist oder die Kamera eine Person sieht (falls du diese Option eingeschaltet hast), und noch 20 Sekunden, nachdem die Tür geschlossen wurde oder die Person gegangen ist.
3. **Nicht im Bett**, solange der Präsenzsensor aus ist.
4. **Weint**, sobald 8 Sekunden lang ununterbrochen Weinen oder 3 Sekunden lang Schreien zu hören war. Ist die Wein-Dauer bis zur Warnung kürzer als 8 Sekunden (durch „Empfindlichkeit" oder den Babysitter-Modus), folgt der Zustand dieser kürzeren Zeit, damit er nie hinter der Warnung zurückbleibt. Der Zustand bleibt „Weint", bis 60 Sekunden lang keines von beiden zu hören war; dann wird er „Wach".
5. Sonst bewegt sich der Zustand so:

| Von | Nach | Wann |
|---|---|---|
| Schläft | Unruhig | 20 Sekunden ununterbrochen Bewegung oder Geräusch |
| Unruhig | Schläft | 120 Sekunden ruhig |
| Unruhig | Wach | 180 Sekunden nach Beginn der Unruhe immer noch Bewegung oder Geräusch |
| Wach | Schläft | 300 Sekunden ruhig |
| Betreut, Nicht im Bett | Wach | Sobald der Grund endet; das Kind gilt als wach, bis es 300 Sekunden ruhig war |
| Unbekannt | Schläft oder Wach | Wenn das Signal zurück ist: schläft, wenn in diesem Moment weder Bewegung noch Geräusch da ist, sonst wach |

Diese sieben Zeiten sind in dieser Version fest. Der Plan sieht vor, sie je Altersprofil einstellbar zu machen; das ist nicht umgesetzt.

Der Zustand wird auch bei ausgeschalteter Überwachung bestimmt. Nur die Alarme hängen am Schalter.

Mit den Aktionen `checkbaby.start_sleep` und `checkbaby.end_sleep` kannst du den Zustand von Hand auf „Schläft" oder „Wach" setzen; die Regeln laufen von dort weiter.

## Welche Alarme es gibt

| Alarmgrund | Stufe | Wann |
|---|---|---|
| Weinen | Warnung, dann kritisch | 15 Sekunden ununterbrochen Weinen oder Schreien (einstellbar, skaliert durch Empfindlichkeit und Modus). Kritisch, sobald die Warnung 180 Sekunden unbeantwortet ist (einstellbar). Er endet, wenn der Zustand „Weint" verlässt, also etwa eine Minute nach dem Ende des Weinens, oder wenn jemand hereinkommt. |
| Keine Atembewegung | Kritisch | Siehe [Vitalquellen](vital-sources.md). Wird nur aufgezeichnet und nicht gemeldet, solange der Schalter „Atembewegungs-Alarm" aus ist. |
| Risiko für die Atemwege, Bauchlage, Lose Gegenstände im Bett, Kamerablick verdeckt | Hinweis bis kritisch | Nur aus der KI-Bewertung, siehe [KI-Bewertung](ai-assessment.md). |
| Bett verlassen | Warnung | Nur im Profil Kleinkind: Der Präsenzsensor wechselt von an auf aus, während niemand beim Kind ist. |
| Haustier im Bett | Warnung | Frigate sieht eine Katze oder einen Hund in der Bett-Zone. |
| Raumklima | Hinweis oder Warnung | Die Raumtemperatur liegt seit 10 Minuten außerhalb des eingestellten Bereichs. Warnung bei mehr als 3 °C Abweichung, sonst Hinweis. Die Luftfeuchte wird nur angezeigt. |
| Rauch oder CO | Kritisch | Einer der eingerichteten Melder ist an. Wird durchgereicht, auch wenn die Überwachung aus oder der Privatmodus an ist. |
| Überwachung gestört | Hinweis, oder Warnung, dann kritisch | Es gibt mindestens eine Störung der Überwachung. Eine leichte Störung ist ein Hinweis. Jede andere Störung ist eine Warnung und wird nach 5 Minuten kritisch. Siehe [Ausfallüberwachung](#die-ausfallüberwachung). |
| Kein Internet | Hinweis | Der Sensor für die Internetverbindung ist aus. |
| Überwachung war unterbrochen | Warnung | Nach einem Start: Die Überwachung war an, und CheckBaby lief zwei Minuten oder länger nicht. |
| Testalarm | Kritisch (oder Warnung) | Du hast „Testalarm" gedrückt. |

Außer Rauch und Testalarm entstehen Alarme nur, solange **die Überwachung an und der Privatmodus aus** ist. Im Zustand „Betreut" pausieren Weinen, keine Atembewegung, Bett verlassen und die KI-Alarme und werden gelöscht; Überwachung gestört, Raumklima, Haustier, Internet und Rauch bleiben aktiv.

Schreien wird nicht sofort kritisch. Es zählt wie Weinen mit kürzerer Bestätigungszeit; kritisch wird es über die Regel „seit drei Minuten unbeantwortet".

## Die drei Alarmstufen

Der Sensor **Alarmstufe** zeigt die höchste Stufe unter den aktiven Alarmen, **Alarmgrund** zeigt, welcher Alarm das ist.

### Hinweis

Es wird nichts gesendet. Der Alarm erscheint in den beiden Sensoren und im Ereignisprotokoll des Diagnose-Downloads.

### Warnung

1. **Sofort:** eine Benachrichtigung an das Handy, das Dienst hat (an alle Handys, wenn „Hat Dienst" auf „Alle" steht, und im Babysitter-Modus immer an alle). Sie enthält das Kamerabild und drei Knöpfe: **Gesehen**, **5 min Ruhe** und **Live**, der dein Dashboard öffnet. Unter iOS wird sie als zeitkritisch („time-sensitive") gesendet.
2. **Nach 60 Sekunden ohne Reaktion**, nur bei Weinen und „Bett verlassen": Der lokale Alarm wird eingeschaltet. Solange der Sensor für die Internetverbindung aus ist, geschieht das sofort.
3. **Nach 180 Sekunden ohne Reaktion:** Die Benachrichtigung wird noch einmal gesendet, jetzt an alle Handys.

Endet dieselbe Warnung und kommt innerhalb von 120 Sekunden wieder, wird sie ohne neue Benachrichtigung wieder aktiv. So lässt ein flackerndes Signal dein Handy nicht alle paar Sekunden brummen. Die Regel schaut nur auf eine Warnung, die tatsächlich auf den Handys war: Ein Hinweis, der endet, ein Alarm, der nur aufgezeichnet wurde, oder eine Warnung, die „5 min Ruhe" zurückgehalten hat, hält die erste Benachrichtigung der nächsten Warnung nicht zurück.

### Kritisch

1. **Sofort:** eine Benachrichtigung an alle Handys, egal wer Dienst hat. Unter iOS wird sie als kritischer Hinweis in voller Lautstärke gesendet, unter Android über den Kanal `alarm_stream`, damit sie trotz Stummschaltung und „Nicht stören" ertönt. Dafür braucht es eine Berechtigung auf dem Handy, siehe [Fehlersuche](troubleshooting.md#ein-kritischer-alarm-ertönt-nicht).
2. **Alle 30 Sekunden:** Die Benachrichtigung wird wiederholt, bis jemand quittiert oder die Ursache endet.
3. **Lokaler Alarm:** Er wird eingeschaltet, sobald eine Benachrichtigung dieses Alarms 60 Sekunden unbeantwortet ist (sofort, solange das Internet ausgefallen ist). Die Minute zählt ab der ersten unbeantworteten Benachrichtigung, auch wenn das noch eine Warnung war. Ein Alarm, der kritisch wird, nachdem seine Warnung eine Minute oder länger unbeachtet blieb, schaltet den lokalen Alarm deshalb zusammen mit dem Schritt zu kritisch ein.

Kritische Alarme werden nie durch Schlummern oder die 120-Sekunden-Regel zurückgehalten.

Der lokale Alarm folgt dem Stand der Alarme. Er ist an, solange ein unbeantworteter Alarm die lokale Stufe erreicht hat, und er wird ausgeschaltet, sobald dieser Alarm quittiert, geschlummert oder vorbei ist.

Ein lokaler Alarm, der schon an ist, bleibt an, wenn seine Warnung kritisch wird.

### Beispiel: Weinen, auf das niemand reagiert

Mit den Standardwerten, gezählt ab dem Moment, in dem Frigate Weinen meldet:

| Zeit | Was passiert |
|---|---|
| 8 s | Der Zustand wird „Weint". |
| 15 s | Warnung an das Handy, das Dienst hat. |
| 75 s | Lokaler Alarm an. |
| 195 s | Der Alarm wird kritisch: Benachrichtigung an alle Handys. Der lokale Alarm bleibt an. |
| danach alle 30 s | Die kritische Benachrichtigung wird wiederholt. |

Die Wiederholung an alle Handys nach 180 Sekunden fällt hier mit dem Schritt zu kritisch zusammen; du siehst also eine Benachrichtigung, nicht zwei.

## Wo ein Alarm ankommt

Eine Warnung oder ein kritischer Alarm kann drei Wege nehmen: das Handy, die Benachrichtigungen von Home Assistant selbst und den lokalen Alarm. Ein Hinweis nimmt keinen davon; er steht nur in den Sensoren.

### Das Handy ist der Hauptalarm

Die Benachrichtigung der Home-Assistant-App ist das, was dich wecken soll. Ein kritischer Alarm wird so gesendet, dass er ertönt, obwohl das Handy stumm ist oder „Nicht stören" eingeschaltet hat. Das Handy muss das erlauben, siehe [Fehlersuche](troubleshooting.md#ein-kritischer-alarm-ertönt-nicht).

Eine Benachrichtigung läuft normalerweise von Home Assistant über die Server von Apple oder Google zum Handy. Sie braucht deshalb das Internet, zu Hause und am Handy. Laut ihrer Dokumentation kann die Home-Assistant-App Benachrichtigungen auch direkt über das Heimnetz empfangen: unter Android mit der Einstellung „Persistent connection" (dauerhafte Verbindung) in den Einstellungen der App, unter iOS als „Local Push", solange das Handy in einem WLAN ist, das in der App als intern eingetragen ist. Das ist eine Funktion der App, die du dort einschaltest. CheckBaby wurde damit nicht ausprobiert.

### Die Benachrichtigungen von Home Assistant

Jede Warnung und jeder kritische Alarm erscheint zusätzlich in den Benachrichtigungen von Home Assistant selbst (die Glocke in der Seitenleiste). So ist auch ohne Handy immer etwas zu sehen, zum Beispiel auf einem Tablet an der Wand.

- Der Eintrag entsteht, wenn der Alarm zum ersten Mal gesendet wird, und wird erneuert, wenn der Alarm eine Stufe steigt.
- Er verschwindet, wenn der Alarm endet, wenn jemand auf „Gesehen" tippt oder wenn die Warnung mit „5 min Ruhe" zurückgehalten wird.
- Ein **Testalarm** schreibt einen zweiten Eintrag, den Zustellbericht. Er nennt, welche Benachrichtigungsdienste die Nachricht angenommen haben, welche nicht erreichbar waren, welche Geräte als lokaler Alarm eingetragen sind und welche davon nicht erreichbar sind, und er sagt, was du am Handy prüfen kannst, wenn dort nichts erschienen ist. Der Bericht bleibt stehen, auch nachdem der Test beantwortet ist. „Angenommen" heißt: Home Assistant hat die Nachricht ohne Fehler übergeben. Ob sie auf dem Handy erschienen ist, kannst nur du sehen.
- Die Ergebnisse der Tasten „Schnell-Check", „Nachtbericht senden" und „KI-Check jetzt" erscheinen ebenfalls dort, siehe [Entitäten und Aktionen](entities-and-actions.md#tasten).

Diese Einträge machen kein Geräusch. Sie sind ein Ort zum Nachsehen, kein Alarm.

### Der lokale Alarm

Das Feld „Lokaler Alarm (Sirene, Licht, Schalter)" ist für Geräte, die Home Assistant selbst schaltet. Das ist der Weg, der ganz ohne Internet funktioniert, solange das Gerät lokal gesteuert wird und nicht über die Cloud seines Herstellers. Wann er einschaltet, steht unter [Die drei Alarmstufen](#die-drei-alarmstufen).

Das Gerät muss in Home Assistant erreichbar sein. Eine smarte Lampe, die am Wandschalter aus ist, bleibt dunkel; die Ausfallüberwachung meldet das als `local_alarm`, siehe [Ausfallüberwachung](#die-ausfallüberwachung).

### Wanddisplays und Tablets

Ein Wanddisplay oder ein Tablet, das ein Dashboard von Home Assistant zeigt, kann Alarme ebenfalls anzeigen:

- **Im Dashboard:** Eine bedingte Karte auf dem Binärsensor „Unbeantworteter Alarm" ist nur sichtbar, solange eine Warnung oder ein kritischer Alarm unbeantwortet ist. Das [Beispiel-Dashboard](../examples/dashboard.de.yaml) enthält eine solche Karte mit der Taste „Gesehen".
- **Als lokaler Alarm:** Hat das Display ein Relais, ein Licht oder eine Sirene, die Home Assistant schalten kann (eine Entität vom Typ Schalter, Licht oder Sirene), kannst du sie unter „Lokaler Alarm" wählen.
- **Ein Ton oder ein blinkendes Licht:** Nimm die Ereignis-Entität „Alarm" in einer eigenen Automation oder die Vorlage [`alert_light.yaml`](../../blueprints/automation/checkbaby/alert_light.yaml), die einem Licht bei einer Warnung eine Farbe gibt und bei einem kritischen Alarm eine andere.

Nichts davon wurde mit einem bestimmten Produkt ausprobiert. Ob ein Display seinen Bildschirm aufweckt oder einen Ton abspielen kann, hängt vom Display ab.

## Quittieren und Schlummern

**Gesehen** (Knopf in der Benachrichtigung, Tasten-Entität oder Aktion `checkbaby.acknowledge`) quittiert alle aktiven Warnungen und kritischen Alarme des Kindes auf einmal.

- Die Benachrichtigungen verschwinden von allen Handys und aus den Benachrichtigungen von Home Assistant, und der lokale Alarm geht aus.
- Wiederholungen und Eskalation hören auf.
- Die Überwachung läuft weiter. Der Alarm bleibt aktiv, solange seine Ursache besteht. Verschlimmert er sich, etwa eine quittierte KI-Warnung, die kritisch wird, meldet er sich erneut.
- Eine quittierte Wein-Warnung wird nicht kritisch.
- Ein Testalarm und „Überwachung war unterbrochen" enden mit der Quittierung.

**5 min Ruhe** (Knopf in der Benachrichtigung, Tasten-Entität oder Aktion `checkbaby.snooze` mit 1 bis 120 Minuten) hält Warnungen zurück.

- Angezeigte Warnungen verschwinden von den Handys und aus den Benachrichtigungen von Home Assistant; neue Warnungen werden nicht gesendet.
- Ein lokaler Alarm, der wegen einer Warnung an ist, wird ausgeschaltet. Der Binärsensor „Unbeantworteter Alarm" bleibt an, weil die Warnung weiter unbeantwortet ist.
- Ist die Zeit um, werden Warnungen, die noch aktiv und unbeantwortet sind, erneut gesendet, an das Handy im Dienst. Ist die Warnung dann älter als 180 Sekunden, folgt die Wiederholung an alle Handys binnen Sekunden. Der lokale Alarm bei Weinen und „Bett verlassen" geht 60 Sekunden nach dem erneuten Senden an, wenn niemand reagiert.
- **Eine Wein-Warnung wird während der Ruhezeit nicht kritisch.** Schlummern zählt als Antwort: Die 180 Sekunden für „niemand reagiert" beginnen, wenn die Ruhezeit endet. Weint das Kind dann noch und quittiert niemand, wird der Alarm 180 Sekunden später kritisch.
- **Andere kritische Alarme kommen trotzdem durch.** Schlummern hält nie einen Alarm zurück, der kritisch ist, zum Beispiel Rauch, eine Störung der Überwachung, die fünf Minuten anhält, oder einen Wein-Alarm, der schon kritisch war. Ein lokaler Alarm, der wegen eines kritischen Alarms an ist, bleibt an.

## Wer Dienst hat

Die Auswahl **Hat Dienst** enthält „Alle" und jedes eingerichtete Handy. Sie bestimmt, wer eine Warnung zuerst bekommt. Kritische Alarme, die Wiederholung nach 180 Sekunden und das Entfernen von Benachrichtigungen gehen immer an alle Handys. Die Ergebnisse von Schnell-Check, Nachtbericht und „KI-Check jetzt" gehen ebenfalls an die Person im Dienst.

## Modi und Empfindlichkeit

**Modus** hat drei Werte:

| Modus | Wirkung |
|---|---|
| Nacht | Der Normalfall. |
| Nickerchen | Verhält sich wie „Nacht". Der Modus wird mit jedem Schlaf im Schlafprotokoll gespeichert. |
| Babysitter | Jede Warnung geht sofort an alle Handys. Die Handys, die unter „Handys der Babysitter" angekreuzt sind (Optionsseite „Wer benachrichtigt wird"), werden zusätzlich zu den Handys der Eltern benachrichtigt; in den anderen Modi bekommen sie nichts. Die Wein-Dauer bis zur Warnung halbiert sich. |

Einen Modus „Aus" gibt es nicht; nimm dafür den Schalter **Überwachung**.

**Empfindlichkeit** skaliert die Wein-Dauer bis zur Warnung: „Niedrig" verdoppelt sie, „Mittel" lässt sie, „Hoch" halbiert sie. Mit dem Standardwert von 15 Sekunden sind das 30, 15 oder 7,5 Sekunden, im Babysitter-Modus jeweils die Hälfte.

## Die Ausfallüberwachung

Ein Babyphone, das still ausfällt, ist schlimmer als keins. Jede Quelle, die der aktive Schlafplatz nutzt, wird überwacht, und jede, die ausfällt, wird zu einer benannten Störung.

| Störung | Überwacht, wenn | Bedeutung |
|---|---|---|
| `mqtt` | Frigate-Kamera oder Vital-Engine | MQTT ist nicht eingerichtet oder nicht verbunden. |
| `frigate` | Frigate-Kamera | Frigate meldet nicht `online`. |
| `audio_level` | Frigate-Kamera, oder Geräuschpegel-Sensor ohne Frigate | Länger als 60 Sekunden kein Geräuschpegel, oder der Pegelsensor hat keinen Wert. |
| `microphone` | Frigate-Kamera | Der Pegel aus Frigate hat sich 10 Minuten lang überhaupt nicht verändert. Ein Geräuschpegel aus einer Sensor-Entität ist ausgenommen, weil ein solcher Wert zu Recht gleich bleiben kann. |
| `cry_sensor` | Wein-Sensor ohne Frigate | Der Wein-Sensor ist nicht verfügbar. |
| `camera` | Kamera-Entität gesetzt | Die Kamera-Entität fehlt oder ist nicht verfügbar. |
| `engine` | ID der Vital-Engine gesetzt | Die Vital-Engine ist offline oder seit mehr als 30 Sekunden stumm. |
| `vital_sensor` | Atemraten-Sensor gesetzt | Der Sensor hat keinen Zahlenwert. |
| `notify` | Immer | Ein eingerichteter Benachrichtigungsdienst existiert nicht, oder es könnte überhaupt niemand alarmiert werden: Es ist kein Handy eingerichtet, und kein Gerät für den lokalen Alarm ist eingetragen oder erreichbar. |
| `local_alarm` | Lokaler Alarm eingetragen | Eine Entität des lokalen Alarms fehlt oder ist in Home Assistant `unavailable` (nicht verfügbar), zum Beispiel eine smarte Lampe, die am Wandschalter aus ist. |
| `sleep_place` | Immer | Kein Schlafplatz ist aktiv. |

Jede Störung wird angezeigt: Der Binärsensor **Störung der Überwachung** geht an, und der Sensor **Störungen der Überwachung** nennt die Namen. Das geschieht auch bei ausgeschalteter Überwachung. Was sonst folgt, hängt vom Grad der Störung ab.

**Leichte Störungen** kosten eine Zugabe, nicht die Überwachung selbst:

- `camera`: Das Bild in Benachrichtigungen und die KI-Bewertung fehlen. Weinen wird weiter erkannt.
- `engine` und `vital_sensor`, solange der Schalter „Atembewegungs-Alarm" aus ist: Dann hängt kein Alarm an diesen Quellen.
- `local_alarm`: Ein Gerät des lokalen Alarms bliebe stumm. Die Handys werden weiter benachrichtigt. Ist kein Handy eingerichtet und keines der Geräte des lokalen Alarms erreichbar, könnte niemand alarmiert werden; das wird als `notify` gemeldet und ist ernst.

Eine leichte Störung sendet keine Benachrichtigung und ändert den Zustand des Kindes nicht. Bei eingeschalteter Überwachung zeigt die Alarmstufe „Hinweis" mit dem Alarmgrund „Überwachung gestört".

**Alle anderen Störungen sind ernst.** Auch `engine` und `vital_sensor` werden ernst, sobald der Schalter „Atembewegungs-Alarm" an ist, weil dann ein Alarm von ihnen abhängt.

- Bei eingeschalteter Überwachung: eine **Warnung** „Überwachung gestört" mit den Gründen im Text, und ein **kritischer Alarm**, wenn die Störung 5 Minuten anhält.
- Liegt die Störung in einer **Kernquelle** (`mqtt` mit Frigate-Kamera, `frigate`, `audio_level`, `cry_sensor`, `sleep_place`), wird außerdem der Zustand „Unbekannt".

Falls du einen Ausfall-Summer nutzt (siehe unten): Sein Lebenszeichen setzt nur aus, solange eine ernste Störung besteht. Eine leichte Störung, zum Beispiel ein ausgefallenes Kamerabild, lässt den Summer nicht ertönen.

Nach einem Start und nach dem Wechsel des Schlafplatzes gilt eine Schonfrist von zwei Minuten, in der eine Quelle, die sich noch nicht gemeldet hat, keine Störung ist. Eine Quelle, die ausdrücklich „offline" oder „nicht verfügbar" meldet, zählt sofort.

Zwei weitere Dinge schützen vor einem stillen Ausfall:

- **Wenn Home Assistant herunterfährt**, während die Überwachung an ist, bekommt das Handy im Dienst „Home Assistant wird beendet. (Name) wird nicht überwacht, bis es wieder läuft." Eine Warnung vor einem Update ist geplant, aber nicht umgesetzt.
- **Ein Ausfall-Summer** (auch „Dead-Man-Summer" genannt) ist ein optionales kleines eigenes Gerät, das piept, sobald Home Assistant verstummt: nach einem Absturz oder wenn Strom oder WLAN ausfallen. Ein Beispiel mit einem ESP32 liegt in [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml). Ein solches Gerät braucht ein regelmäßiges Lebenszeichen. Wähle seine Taste unter „Lebenszeichen für einen Ausfall-Summer (optional)" auf der Optionsseite „Wer benachrichtigt wird": CheckBaby drückt sie alle 30 Sekunden, solange die Überwachung an ist und keine ernste Störung besteht. Bleibt das Drücken aus, ertönt der Summer. Hast du kein solches Gerät, lass das Feld leer.

Wenn du einen Sensor für die Internetverbindung eingerichtet hast, löst sein „aus" den Hinweis „Kein Internet" aus und lässt den lokalen Alarm sofort statt nach einer Minute auslösen, weil die Push-Nachrichten normalerweise vom Internet abhängen.

## Der gelernte Grundpegel

Weißes Rauschen oder ein Luftbefeuchter heben den Geräuschpegel über Stunden an. Eine feste Schwelle würde dann die ganze Nacht als laut werten. CheckBaby lernt deshalb den Pegel des Raums und wertet nur als „Geräusch", was um mehr als den Abstand darüber liegt (Zahl **Lautstärke über dem Grundpegel**, Standard 15 dB).

- Der Grundpegel beginnt beim ersten empfangenen Pegel und folgt dem Pegel danach langsam, mit einer Zeitkonstante von zehn Minuten.
- Er lernt nur aus ruhigen Momenten und nie, während Weinen oder Schreien zu hören ist. Weinen hebt ihn also nicht an.
- Geräusch, das fünf Minuten lang einfach bleibt, ohne dass geweint wird, gilt als Eigengeräusch des Raums; von da an folgt ihm der Grundpegel nach oben.
- Der Grundpegel steht im Diagnose-Sensor **Gelernter Grundpegel** und übersteht Neustarts.

Grundpegel und Abstand entscheiden zwischen „Schläft", „Unruhig" und „Wach" und öffnen die Ton-Weiterleitung. Den Wein-Alarm lösen sie **nicht** aus: Der kommt nur aus der Wein- und Schrei-Erkennung von Frigate (oder deinem Wein-Sensor).

## Ton-Weiterleitung

Wenn du auf der Optionsseite „Weitere Geräte und Einstellungen" einen Lautsprecher und im Schlafplatz die Adresse eines Ton-Streams einträgst und den Schalter **Ton-Weiterleitung** einschaltest, spielt CheckBaby den Stream nach zwei Sekunden Geräusch oder Weinen auf dem Lautsprecher ab und beendet ihn nach 60 Sekunden Ruhe. Das funktioniert nur, solange die Überwachung an und der Privatmodus aus ist. Ob dein Lautsprecher den Stream abspielt und mit welcher Verzögerung, musst du ausprobieren; das ist ungetestet.

## Privatmodus

Der Schalter **Privatmodus** ist für Momente wie das Stillen vor der Kamera gedacht.

Solange er an ist:

- Der Zustand zeigt „Unbekannt".
- Es entstehen keine Alarme, und von selbst wird nichts gesendet, mit einer Ausnahme: Rauch und CO. Eine Taste, die du selbst drückst („Testalarm", „Schnell-Check", „Nachtbericht senden"), zeigt ihr Ergebnis weiterhin.
- Es wird kein Bild an eine KI-Aufgabe gesendet: weder automatisch noch mit der Taste „KI-Check jetzt" oder den Aktionen `checkbaby.assess_now` und `checkbaby.quick_check`. Die Taste meldet dann nur, dass der Privatmodus an ist.
- Die Ton-Weiterleitung hält an. „Ruhezeit" ist aus.

Was der Privatmodus **nicht** tut:

- Er schaltet weder die Kamera noch Frigate noch Frigates Aufzeichnung ab. Darauf hat CheckBaby keinen Einfluss.
- Er hält das Lebenszeichen für einen Ausfall-Summer nicht an.

## Was einen Neustart übersteht

Wird in Home Assistant auf der Festplatte gespeichert und beim Start wiederhergestellt:

- jede Einstellung, die du über die Entitäten vornimmst (Überwachung, Privatmodus, Modus, Hat Dienst, Empfindlichkeit, Schwellen, der aktive Schlafplatz, ein laufendes Schlummern),
- die aktiven Alarme einschließlich der Quittierung,
- das Schlafprotokoll (Schlafphasen, Aufwachen, Wein-Zeiten),
- der gelernte Grundpegel,
- ob der lokale Alarm an war, damit er sich noch ausschalten lässt.

Nicht gespeichert: der Zustand des Kindes und die letzten Signale. Nach einem Start ist der Zustand „Unbekannt", bis sich die Quellen gemeldet haben, und es gilt die Schonfrist von zwei Minuten.

War die Überwachung an und CheckBaby zwei Minuten oder länger weg, bekommst du die Warnung „Die Überwachung von (Name) war N min unterbrochen".

Die Daten werden etwa alle 15 Sekunden gespeichert und wenn Home Assistant stoppt. Beim Entfernen des Eintrags werden sie gelöscht.

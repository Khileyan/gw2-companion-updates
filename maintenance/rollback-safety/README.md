# Fixed-path Rollback-Safety-Korrektur (Entwicklungsstand, noch nicht veröffentlicht)

Dieser Patch ist **kein** freigegebenes oder signiertes Update. Er darf nicht direkt in eine laufende Windows-Installation kopiert werden. Er wurde gegen den lokalen RC8-Entwicklungsstand abgeleitet. Vor Release sind ein Abgleich mit dem exakt publizierten RC8-Quellstand, die komplette Regression und Windows-End-to-End-Test nötig.

## Anlass
Auf dem Nutzer-PC blieb nach RC6→RC7 ein Journal `phase=starting` bestehen, obwohl RC7 bereits verbunden gewesen war. `restoreFixed` schlug fehl (`fixed_rollback_failed`), und `Start-Managed.ps1` blockierte reguläre Starts. Das ist kein Beweis, welcher Windows-Handle den Rollback verhinderte.

## Implementiert in der isolierten Entwicklungskopie
- Finalisierung schreibt zuerst `last-good.json`, dann `phase=committed` und behandelt spätere Sperrfehler beim Entfernen des alten Backups als reinen Aufräumbedarf, nicht als Grund für destruktives Zurückrollen.
- Der reguläre Starter darf ein verbliebenes `committed`-Journal ausschließlich nach konsistenter Prüfung des `last-good`-Belegs und der aktiven Versionsmetadaten akzeptieren. Andere Journale blockieren weiterhin.
- Die Wiederherstellung versucht `EPERM`/`EBUSY`/`EACCES` nach kurzer Pause begrenzt erneut, aber keine sonstigen Fehler.
- Wenn ein nachweislich verbundener Kandidat erst bei der Finalisierung scheitert, wird kein automatischer Rollback mehr erzwungen.
- Sieben isolierte Node-Regressionstests bestehen.

## Offen / Freigabesperre
1. Vergleich mit dem exakt auf GitHub veröffentlichten RC8-Asset und dessen SHA256.
2. Vollständige vorhandene Test-Suite erneut ausführen und Integrationstests ergänzen.
3. Sicherer Windows-Test mit Dateisperren und neuer Transaktion, kontrollierter Wiederverbindung und Rollback.
4. Erst danach als neue eindeutig versionierte, signierte Version über den vorhandenen GitHub-Updater verteilen. Bereits signierte RC8-Assets dürfen nicht stillschweigend überschrieben werden.

Der laufende RC7, `preview.json` und alte Rollback-Verzeichnisse bleiben unangetastet.
# GW2 Account Companion – signierte Updates

Dieses Repository dient ausschließlich als öffentlicher **Verteiler für signierte Programmupdates** des privat betriebenen GW2 Account Companion. Es ist **nicht** das Entwicklungsrepository.

## Status

**Noch kein Release veröffentlicht.** Es gibt derzeit weder ein gültiges `preview.json` noch `stable.json`. Alle in Anleitungen gezeigten Versionsnummern und Download-URLs sind bis zu einer ausdrücklichen Releasefreigabe Beispiele.

## Sicherheitsmodell

- Der Herausgeber erstellt das **Ed25519-Schlüsselpaar lokal auf seinem Windows-Rechner**. Der private Schlüssel darf niemals in dieses Repository, ein Release-ZIP, den Companion-Installationsordner oder einen Chat gelangen.
- Der Companion akzeptiert ausschließlich Manifeste mit gültiger Ed25519-Signatur des **vorab lokal angepinnten öffentlichen Schlüssels**. Das Manifest darf den Vertrauensschlüssel nicht selbst festlegen.
- Der verifizierte Manifestinhalt enthält Versionsnummer, Kanal (`preview` / `stable`), HTTPS-Asset-URL, SHA-256, Paketgröße und Mindest-Updaterversion.
- Vor einer Installation werden Archivstruktur und Paket-Hash geprüft; die Installation erfolgt **erst nach ausdrücklicher lokaler Bestätigung**. Bei fehlgeschlagenem Start ist ein Rollback vorgesehen.
- Ein öffentliches Release-Asset ist für alle lesbar. Die aktuellen ZIP-Pakete enthalten lesbaren JavaScript-Code; deshalb werden hier **keine Dateien ohne gesonderte Freigabe** veröffentlicht.
- Ein Hashwert allein beweist **nicht**, wer ein Paket herausgegeben hat. Erst die Signaturprüfung gegen den unabhängig geprüften und angepinnten Schlüssel schafft diese Bindung.

## Geplante Struktur

- `preview.json`: signiertes Manifest für den Preview-Kanal, **erst nach Veröffentlichung eines passenden geprüften Release-Assets**
- `stable.json`: signiertes Manifest für den Stable-Kanal, **erst nach erfolgreicher Stable-Abnahme**
- GitHub Releases: versionierte Release-Assets, deren Download-URLs im signierten Manifest stehen

## Veröffentlichungsreihenfolge

1. Testbuild und Regression prüfen.
2. Auf dem Besitzer-PC ZIP mit dem **dort verbleibenden privaten Schlüssel** signieren; öffentlichen Schlüssel/Fingerprint getrennt prüfen.
3. Nach Freigabe das geprüfte ZIP als GitHub Release Asset veröffentlichen.
4. Das zu exakt diesem Asset gehörende, signierte Manifest hier einstellen.
5. Im Companion den **öffentlichen** Schlüssel und die Manifest-URL einmalig verankern.
6. Das Update auf Windows inklusive lokaler Freigabe, Health-Check und Rollback testen.

**Keine GW2-API-Schlüssel, persönlichen Einstellungen, Tokens, Accountdaten oder lokalen Datenbanken in dieses öffentliche Repository hochladen.**

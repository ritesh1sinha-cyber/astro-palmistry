# GrahaRekha Android app

A WebView shell around the live site, so the reading can be opened from a phone
home screen instead of a browser tab. The reports, engines and payments all stay
on the server; this project contains no astrology or palmistry logic.

Currently pointed at **https://www.graharekha.com/** (GCP).

## Build

The toolchain is already installed on this machine (Microsoft OpenJDK 17, Gradle
8.7 under `%USERPROFILE%\android-dev`, Android SDK 34 under
`%LOCALAPPDATA%\Android\Sdk`).

```powershell
cd mobile/android
./build_apk.ps1                 # signed release APK -> dist/GrahaRekha-1.0.0.apk
./build_apk.ps1 -Bundle         # Play App Bundle     -> dist/GrahaRekha-1.0.0.aab
./build_apk.ps1 -Dev            # debug APK
./build_apk.ps1 -Install        # build APK, then adb install to a connected phone
```

Or drive Gradle directly:

```powershell
$env:JAVA_HOME = 'C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot'
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
& "$env:USERPROFILE\android-dev\gradle-8.7\bin\gradle.bat" assembleRelease
& "$env:USERPROFILE\android-dev\gradle-8.7\bin\gradle.bat" bundleRelease
```

## Google Play

See **[PLAY_STORE.md](PLAY_STORE.md)** for:

- Version bump rules (`versionCode` / `versionName`)
- Store listing short + full description (ready to paste)
- Data safety / privacy URL / review notes
- Internal testing → production checklist

Upload the **`.aab`** from `./build_apk.ps1 -Bundle`, not the sideload APK.

Current build targets: `compileSdk` / `targetSdk` **35** (Play requirement). Bump
`versionCode` on every Play upload.

## Install on a phone (sideload)

Over USB, which keeps the APK off any public host:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r dist\GrahaRekha-1.0.0.apk
```

Without a cable, copy the APK to the phone over USB mass storage or Bluetooth and
open it from the Files app; Android will ask once for permission to install from
this source. Do not upload the APK to a public file-sharing service to get it onto
the phone.

The debug and release builds carry different application IDs
(`com.graharekha.app.debug` and `com.graharekha.app`), so both can sit on the same
phone at once.

## Pointing it somewhere else

One line in `gradle.properties`:

```properties
graharekha.baseUrl=https://www.graharekha.com/
```

Rebuild after changing it. A `http://` value additionally switches on cleartext
traffic and relaxes mixed-content blocking, which a LAN address such as
`http://192.168.1.20:8000` needs. Reaching a development server that way means
being on the same network or VPN as the machine — do not open a port to the
internet or run a tunnel to make it reachable.

## What the shell has to handle

A default WebView breaks most of this site, so the bulk of `MainActivity` exists
for these four hand-offs:

| Site behaviour | Without handling | Handled by |
| --- | --- | --- |
| Palm capture via `getUserMedia` | Camera silently denied | `onPermissionRequest` plus the app's own `CAMERA` grant |
| Palm upload via `<input type="file">` | Button does nothing | `onShowFileChooser`, with a camera option through `FileProvider` |
| Razorpay handing off to GPay/PhonePe | `ERR_UNKNOWN_URL_SCHEME`, payment dead-ends | `upi:`/`intent:`/vendor schemes launched as intents |
| Report PDFs and new-window reports | Download ignored, `window.open` dropped | `DownloadListener` with the session cookie, and a popup WebView |

Back navigation closes a popup first, then walks the page history, then leaves the
app. Session cookies are flushed on pause so being killed in the background does
not sign the reader out. There is deliberately no pull-to-refresh: an accidental
pull while filling in birth details would throw the form away.

## Signing

`assembleRelease` / `bundleRelease` sign with the keystore named in
`keystore.properties`, which is git-ignored along with the keystore itself
(`%USERPROFILE%\android-dev\graharekha-release.jks`). Without that file the
release variant still builds, just unsigned, so a fresh clone is never blocked
on a secret it does not have.

Keep the keystore backed up. Android identifies an app by its signature, so a
replacement key means every phone must uninstall before it can update (sideload)
or Play updates fail (upload key). For Play, enable **Play App Signing**; your
local keystore becomes the **upload** key — back it up offline and never rotate
casually.

## Known limit: Google Sign-In

Google refuses to render its sign-in button for any user agent carrying the
WebView `wv` token, so the shell presents the underlying Chrome user agent
instead. If Google tightens that check, the sign-in button stops working inside
the app while the promocode login continues to work. Nothing else on the site
depends on it. OAuth uses the same Web client origins as
`https://www.graharekha.com` — no separate Android OAuth client is required for
the current GIS button flow.

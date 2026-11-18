# Teryx Remote for Android

The pocket OS as a real Android app, for a cheap phone that lives in the ATV's
glove box (docs/rc-beach-launch.md, section 4b). It's a thin wrapper round the
same page the iPhone uses (`dash/web/remote.html`), copied into the app when it's
built, so there's only one remote to keep up to date. iPhones can't sideload, so
on iPhone it stays a home-screen web app.

What the app adds over the web page:

- Full screen, landscape, and the screen stays on while it's open.
- It can be the phone's **Home** app, so the phone boots straight into it.
- A full kiosk lock if you make it the device owner (below).
- The back button does nothing (a gamepad's B button can act as back).
- Pulling the charger out (taking it out of the glove box) wakes the screen and
  shows "READY".
- The page is served from inside the app on a secure address, so gamepads work
  with no certificate setup. The Pi can still be plain http on the hotspot.
- Settings has **WI-FI** (join the Teryx's hotspot) and **PHONE SETTINGS** (behind
  the PIN, the only way out of the kiosk).

The safety rules are not in the app. They're in the RC box: if the app or phone
dies, its packets stop and the Teryx stops and holds.

## Install it (sideload)

1. On the phone, open https://electrumnz.github.io/TERYXDACTL/teryx-remote.apk
   (or download `teryx-remote-apk` from the latest "Android app" run on GitHub
   Actions).
2. Android asks to allow installs from the browser: allow it, install, then turn
   that permission back off.
3. Open Teryx Remote, then Settings > WI-FI and join the Teryx's hotspot once.
   Android rejoins it on its own after that.

## Make it boot straight into the remote

Pick one:

- **Simple:** Android Settings > Apps > Default apps > Home app > Teryx Remote.
  Then also turn on app pinning (Settings > Security > App pinning) and pin it.
  Menu names differ between brands.
- **Full kiosk lock (needs a computer once):** on a freshly reset phone with no
  Google account added, turn on USB debugging and run

  ```
  adb shell dpm set-device-owner nz.teryx.remote/.AdminReceiver
  ```

  The app then locks itself on screen and the only way out is PHONE SETTINGS
  with the PIN. To undo it, factory reset the phone.

## Updates

Each build gets a higher version number. Updates install over the top only if
every build is signed with the same key. Until the repo has one, builds use a
throwaway debug key, so you'd uninstall first. To set a key up once:

```
keytool -genkeypair -v -keystore teryx.jks -alias teryx -keyalg RSA -keysize 4096 -validity 10000
base64 -w0 teryx.jks
```

Then add GitHub repo secrets `TERYX_KEYSTORE_B64` (the base64 text),
`TERYX_KEYSTORE_PASSWORD`, `TERYX_KEY_ALIAS` (teryx) and `TERYX_KEY_PASSWORD`.
Keep `teryx.jks` somewhere safe and never commit it.

## Build it yourself

Needs Java 17, Gradle 8.9 or newer and the Android SDK (platform 35).

```
cd android
gradle assembleRelease
# app/build/outputs/apk/release/app-release.apk
```

## Licences

Our code is MIT like the rest of the repo. It uses AndroidX WebKit (Apache 2.0),
which is fine to ship with MIT code. The fonts in the page are SIL OFL (licence
files ship with them).

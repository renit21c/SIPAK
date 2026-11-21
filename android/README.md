# SIPAK Android

Native Android WebView application for https://sipak.up.railway.app/. Package `com.sipak.app`, Android 8.0+ (API 26), version 1.0.0. The APK uses the hosted service and requires internet. Web changes are available without rebuilding the APK while the hosting address remains the same.

## Build

Install JDK 17–24 and Google's Android SDK command-line tools. Accept the Android SDK license, then install `platforms;android-35`, `build-tools;35.0.0` and `platform-tools`. The included Gradle wrapper downloads and verifies Gradle 8.14.3. Default local tooling directory is the ignored `tmp/android-tooling/`.

```powershell
./scripts/build-android.ps1 -JavaPath 'C:/Program Files/Java/jdk-24'
```

For another installation, pass `-SdkPath`, `-GradlePath`, and `-JavaPath`. Output is `output/android/SIPAK-1.0.0.apk`. The build checks Android lint as well as compilation.

First release build creates a signing key and password in ignored `android/signing/`. Keep a private backup of that whole folder: future updates must use the same key. Never commit it or put it in the APK. Increment versionCode/versionName for subsequent versions in app/build.gradle.

## Behavior

- Only the SIPAK HTTPS origin is loaded in the privileged main WebView. Other web links use the browser; SSL errors are rejected.
- Login cookies stay within the app's WebView. The app contains no account password or API key.
- File inputs use the Android document picker; no broad storage permission is requested.
- BAP and recommendation PDF links open Save As. The native download keeps the same SIPAK login cookie and never forwards it to another host or through redirects.
- Back follows web history before exiting. System bars, display cutouts and the keyboard have inset handling. Network failures offer retry.
- App data is excluded from Android backup. No JavaScript/native bridge is exposed.

Test upload, authenticated PDF download, back navigation, rotation, keyboard and relaunch on a real Android device before broad distribution. Browser web checks alone do not verify WebView/native integration. This APK does not publish the app to Google Play.

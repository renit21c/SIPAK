param(
    [string]$SdkPath = '',
    [string]$GradlePath = '',
    [string]$JavaPath = ''
)
$ErrorActionPreference = 'Stop'
$sipakRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $sipakRoot
if (-not $SdkPath) { $SdkPath = Join-Path $sipakRoot 'tmp/android-tooling/sdk' }
if (-not $GradlePath) { $GradlePath = Join-Path $sipakRoot 'android/gradlew.bat' }
if ($JavaPath) { $env:JAVA_HOME = $JavaPath }
if (-not $env:JAVA_HOME) { throw 'Set JAVA_HOME to JDK 17–24, or pass -JavaPath.' }
if (-not (Test-Path -LiteralPath "$SdkPath/platforms/android-35/android.jar")) { throw 'Install Android SDK platform 35 and build-tools 35.0.0 first. See android/README.md.' }
if (-not (Test-Path -LiteralPath $GradlePath)) { throw 'Pass -GradlePath with a Gradle 8.14.3 executable.' }
$env:ANDROID_HOME = (Resolve-Path -LiteralPath $SdkPath).Path
$env:PATH = "$env:JAVA_HOME/bin;$env:PATH"
$sipakSigning = Join-Path $sipakRoot 'android/signing'
$sipakKey = Join-Path $sipakSigning 'sipak-release.p12'
$sipakProperties = Join-Path $sipakSigning 'keystore.properties'
New-Item -ItemType Directory -Force -Path $sipakSigning | Out-Null
if (-not (Test-Path -LiteralPath $sipakKey)) {
    $sipakRandom = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($sipakRandom)
    $env:SIPAK_ANDROID_KEY_PASSWORD = [Convert]::ToBase64String($sipakRandom)
    try {
        & "$env:JAVA_HOME/bin/keytool.exe" -genkeypair -keystore $sipakKey -storetype PKCS12 -alias sipak -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=SIPAK, OU=Android, O=SIPAK, C=ID' -storepass:env SIPAK_ANDROID_KEY_PASSWORD -keypass:env SIPAK_ANDROID_KEY_PASSWORD
        if ($LASTEXITCODE -ne 0) { throw 'Release key creation failed.' }
        [IO.File]::WriteAllText($sipakProperties, "storeFile=signing/sipak-release.p12`nstorePassword=$env:SIPAK_ANDROID_KEY_PASSWORD`nkeyAlias=sipak`nkeyPassword=$env:SIPAK_ANDROID_KEY_PASSWORD`n")
    } finally { Remove-Item Env:SIPAK_ANDROID_KEY_PASSWORD -ErrorAction SilentlyContinue }
}
if (-not (Test-Path -LiteralPath $sipakProperties)) { throw 'Restore the original signing/keystore.properties; do not replace the existing release key.' }
$sipakSdkProperty = $env:ANDROID_HOME.Replace('\','/')
[IO.File]::WriteAllText((Join-Path $sipakRoot 'android/local.properties'),"sdk.dir=$sipakSdkProperty`n")
& $GradlePath --project-dir "$sipakRoot/android" --gradle-user-home "$sipakRoot/tmp/android-tooling/gradle-home" --no-daemon assembleRelease lintRelease
if ($LASTEXITCODE -ne 0) { throw 'Android build or checks failed.' }
$sipakBuildTools = Join-Path $env:ANDROID_HOME 'build-tools/35.0.0'
$sipakRelease = Join-Path $sipakRoot 'android/app/build/outputs/apk/release/app-release.apk'
& "$sipakBuildTools/apksigner.bat" verify --verbose $sipakRelease
if ($LASTEXITCODE -ne 0) { throw 'APK signature verification failed.' }
& "$sipakBuildTools/zipalign.exe" -c 4 $sipakRelease
if ($LASTEXITCODE -ne 0) { throw 'APK alignment verification failed.' }
$sipakOutput = Join-Path $sipakRoot 'output/android'
New-Item -ItemType Directory -Force -Path $sipakOutput | Out-Null
Copy-Item -LiteralPath "$sipakRoot/android/app/build/outputs/apk/release/app-release.apk" -Destination "$sipakOutput/SIPAK-1.0.0.apk"
$sipakHash = Get-FileHash -LiteralPath "$sipakOutput/SIPAK-1.0.0.apk" -Algorithm SHA256
[IO.File]::WriteAllText("$sipakOutput/SIPAK-1.0.0.apk.sha256",$sipakHash.Hash.ToLowerInvariant()+"  SIPAK-1.0.0.apk`n")
$sipakHash | Format-List
Write-Output "APK: $sipakOutput/SIPAK-1.0.0.apk"

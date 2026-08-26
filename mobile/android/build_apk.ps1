<#
Builds the GrahaRekha APK or Play Store AAB.

Gradle and the Android SDK are not on PATH, so this script points at them itself
rather than relying on a shell that happens to be set up correctly.

    ./build_apk.ps1              # signed release APK -> dist/GrahaRekha-x.y.z.apk
    ./build_apk.ps1 -Bundle      # Play App Bundle     -> dist/GrahaRekha-x.y.z.aab
    ./build_apk.ps1 -Dev         # debug APK
    ./build_apk.ps1 -Install     # also push APK to a phone over USB (not with -Bundle)
#>
param(
    # Not named -Debug: PowerShell reserves that as a common parameter.
    [switch]$Dev,
    [switch]$Install,
    [switch]$Bundle
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if ($Bundle -and $Dev) {
    throw '-Bundle is release-only. Omit -Dev when building a Play AAB.'
}
if ($Bundle -and $Install) {
    throw '-Install only works with an APK. Build with -Bundle, then upload the .aab to Play Console.'
}

$jdk = (Get-ChildItem 'C:\Program Files\Microsoft' -Directory |
        Where-Object Name -like 'jdk-17*' | Select-Object -First 1).FullName
if (-not $jdk) { throw 'JDK 17 not found under C:\Program Files\Microsoft.' }

$gradle = "$env:USERPROFILE\android-dev\gradle-8.7\bin\gradle.bat"
if (-not (Test-Path $gradle)) { throw "Gradle not found at $gradle." }

$env:JAVA_HOME = $jdk
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME

$variant = if ($Dev) { 'debug' } else { 'release' }
$task = if ($Bundle) {
    'bundleRelease'
} else {
    'assemble' + [char]::ToUpper($variant[0]) + $variant.Substring(1)
}

& $gradle $task
if ($LASTEXITCODE -ne 0) { throw "Gradle $task failed." }

$match = Select-String -Path 'app\build.gradle' -Pattern "versionName '(.+)'"
$version = $match.Matches[0].Groups[1].Value
$suffix = if ($Dev) { '-debug' } else { '' }

New-Item -ItemType Directory -Force -Path dist | Out-Null

if ($Bundle) {
    $src = "app\build\outputs\bundle\release\app-release.aab"
    if (-not (Test-Path $src)) { throw "AAB not found at $src" }
    $out = "dist\GrahaRekha-$version.aab"
    Copy-Item $src $out -Force
    Write-Host "AAB (upload this to Play Console): $(Resolve-Path $out)"
} else {
    $src = "app\build\outputs\apk\$variant\app-$variant.apk"
    if (-not (Test-Path $src)) { throw "APK not found at $src" }
    $out = "dist\GrahaRekha-$version$suffix.apk"
    Copy-Item $src $out -Force
    Write-Host "APK: $(Resolve-Path $out)"
}

if ($Install) {
    $adb = "$env:ANDROID_HOME\platform-tools\adb.exe"
    if (@(& $adb devices | Select-String -Pattern '\tdevice$').Count -eq 0) {
        throw 'No phone visible to adb. Enable USB debugging and reconnect.'
    }
    & $adb install -r $out
}

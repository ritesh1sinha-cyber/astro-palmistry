"""Confirm the built APK/AAB carry the config we think they do.

Reads BuildConfig out of the compiled dex and the version out of the bundle's
protobuf manifest, so the check is on the artifact rather than on build.gradle.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

APK = Path("dist/GrahaRekha-1.0.5.apk")
AAB = Path("dist/GrahaRekha-1.0.5.aab")

fail = []


def strings_in(blob: bytes, pattern: str) -> list[str]:
    return sorted({m.decode("utf-8", "ignore")
                   for m in re.findall(pattern.encode(), blob)})


print("=" * 66)
print("APK", APK, f"{APK.stat().st_size:,} bytes")
print("=" * 66)
with zipfile.ZipFile(APK) as z:
    names = z.namelist()
    dex = b"".join(z.read(n) for n in names if n.endswith(".dex"))
    print(f"  entries: {len(names)}  dex bytes: {len(dex):,}")

    urls = strings_in(dex, r"https?://[A-Za-z0-9./_\-]{6,60}")
    print("  URLs compiled into the app:")
    for u in urls:
        print(f"    {u}")
    if not any("graharekha.com" in u for u in urls):
        fail.append("APK does not contain the graharekha.com base URL")
    # schemas.android.com is the XML namespace URI, not an endpoint.
    plaintext = [u for u in urls
                 if u.startswith("http://")
                 and not u.startswith("http://schemas.android.com/")
                 and "localhost" not in u and "127.0.0.1" not in u]
    if plaintext:
        fail.append(f"APK ships a plaintext http:// endpoint: {plaintext}")
    else:
        print("  ok  no plaintext endpoint compiled in")

    # The WebView cache purge is keyed on this, so it must be the new code.
    if b"lastVersionCode" not in dex:
        fail.append("APK is missing the version-keyed WebView cache purge")
    else:
        print("  ok  version-keyed WebView cache purge present")

print()
print("=" * 66)
print("AAB", AAB, f"{AAB.stat().st_size:,} bytes")
print("=" * 66)
with zipfile.ZipFile(AAB) as z:
    names = z.namelist()
    print(f"  entries: {len(names)}")
    manifest = z.read("base/manifest/AndroidManifest.xml")
    vnames = strings_in(manifest, r"\d+\.\d+\.\d+")
    print(f"  versionName strings in manifest: {vnames}")
    if "1.0.5" not in vnames:
        fail.append(f"AAB manifest does not carry versionName 1.0.5: {vnames}")
    # versionCode is a varint; 6 appears right after the versionCode attr name.
    if b"versionCode" not in manifest:
        fail.append("AAB manifest has no versionCode attribute")
    if b"com.graharekha.app" not in manifest:
        fail.append("AAB manifest has the wrong applicationId")
    else:
        print("  ok  applicationId com.graharekha.app")
    if not any(n.endswith(".RSA") or n.endswith(".DSA") or n.endswith(".EC")
               for n in names) and "META-INF/MANIFEST.MF" not in names:
        print("  note bundle signature lives in the JAR block (checked by Play)")

print()
if fail:
    print(f"{len(fail)} PROBLEM(S)")
    for f in fail:
        print(f"  FAIL {f}")
    sys.exit(1)
print("ARTIFACTS VERIFIED")

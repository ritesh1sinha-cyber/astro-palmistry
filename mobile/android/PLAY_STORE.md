# GrahaRekha — Google Play Store guide

Package: `com.graharekha.app`  
Live site (WebView): `https://www.graharekha.com/`  
Privacy: `https://www.graharekha.com/#/privacy`  
Terms: `https://www.graharekha.com/#/terms`  
Support email: `admin@graharekha.com`

---

## Versioning (every Play upload)

Edit `app/build.gradle` → `defaultConfig`:

| Field | Rule |
|--------|------|
| `versionCode` | Integer. **Must increase** every upload (1 → 2 → 3…). Play rejects reuse. |
| `versionName` | User-visible string (`1.0.0` → `1.0.1` → `1.1.0`). |

Current: `versionCode 5` / `versionName 1.0.4` / `targetSdk 36`.

Sideload APKs and Play AABs share the same counters. Bump before `./build_apk.ps1 -Bundle`.

---

## Build the Play upload (.aab)

```powershell
cd mobile/android
./build_apk.ps1 -Bundle
# → dist/GrahaRekha-<versionName>.aab
```

Requires `keystore.properties` + upload keystore (same files as release APK).  
Play Console → Release → upload the **`.aab`**, not the `.apk`.

Enable **Play App Signing** on first upload (recommended). Keep your upload
keystore backed up forever; losing it blocks updates unless you go through
Play’s reset flow.

---

## Store listing — copy (paste into Play Console)

### App name
```
GrahaRekha
```

### Short description (≤80 characters)
```
Palmistry & Vedic astrology — one confluence reading on your phone.
```
(73 chars)

**Alt short (if you want “AI” softer):**
```
Palm lines + Vedic chart, cross-checked. Free preview, unlock if it fits.
```
(74 chars)

### Full description
```
GrahaRekha brings palmistry and Vedic astrology together into one clear reading — built for your phone.

WHY GRAHAREKHA
• Twelve classical methods cross-checked into one verdict (not one-sign memes)
• Palm lines and Vedic chart confluence — or either on its own
• See a free half of your reading first; pay only if it matches your life
• No birth time? Horary and palm readings still work

WHAT YOU CAN DO
• Capture both palms with the camera or upload photos
• Run a full chart reading, ask one life question, or match kundali
• Save readings to your account with Google Sign-In
• Pay securely with Razorpay (UPI apps like GPay / PhonePe supported)

HOW IT WORKS
Palm contours and line measures are read alongside Swiss Ephemeris positions and classical Jyotish pillars (including dasha timing and KP). The app is a mobile shell: capture, upload, payment handoff, and report download are handled natively so the experience works outside the browser.

Educational astrology and palmistry insights only — not medical, legal, or financial advice.

Privacy: https://www.graharekha.com/#/privacy
Terms: https://www.graharekha.com/#/terms
Website: https://www.graharekha.com
```

### App category
Lifestyle (or Entertainment)

### Tags / keywords (internal — Play no longer has free-form keywords; weave into description)
palmistry, vedic astrology, kundali, horoscope, palm reading, jyotish, birth chart

---

## Graphics checklist

| Asset | Size | Notes |
|--------|------|--------|
| App icon (Hi-res) | 512×512 PNG | No transparency; can derive from `site/img/logo.png` |
| Feature graphic | 1024×500 | Brand + one line: “Palm + chart · one verdict” |
| Phone screenshots | ≥2 (recommend 4–8) | Home, palm capture, sample free report, ask-question |
| 7" / 10" tablet | Optional | Same screens scaled |

Do not upload APKs or AABs to public file hosts to share screenshots devices.

---

## Policy forms (quick answers for this app)

### Privacy policy URL
`https://www.graharekha.com/#/privacy`

### Data safety (declare what you collect)

| Data | Collected? | Purpose |
|------|------------|---------|
| Name, email | Yes (Google Sign-In) | Account |
| Photos | Yes (palm images) | App functionality |
| Personal info (birth date/time/place) | Yes | App functionality |
| Approximate location | Only if user enters place for chart | App functionality |
| Payment info | Processed by Razorpay; you don’t store card numbers | Purchases |
| App activity | Session / readings saved to account | App functionality |

Encryption in transit: **Yes** (HTTPS).  
Users can request deletion: follow your privacy policy / support email.

### Permissions
- `CAMERA` — palm capture  
- `INTERNET` — load site + API  
- Storage (legacy ≤28 only) — report downloads  

### Ads
No

### Target age
Prefer **18+** (astrology / palmistry lifestyle)

### Content rating
Complete IARC questionnaire; typically mild lifestyle / reference content. No gambling unless you add it.

### News / COVID / government apps
No

---

## Review notes (paste when submitting)

```
GrahaRekha is a native WebView shell for https://www.graharekha.com with mobile-specific
integrations that a plain browser tab does not provide:

1. Camera permission + getUserMedia for live palm capture
2. FileProvider camera/gallery path for <input type="file"> palm upload
3. UPI / intent: / vendor URL schemes so Razorpay can hand off to GPay, PhonePe, etc.
4. DownloadListener + session cookies for report PDFs; popup WebView for window.open reports

Astrology and palmistry engines run on our GCP backend. Sign-in uses Google Identity
Services (Web client) on the same origin. Educational use only.
```

---

## Release path (recommended)

1. Play Console → create app → fill listing + Data safety + rating + privacy URL  
2. `./build_apk.ps1 -Bundle` → upload AAB to **Internal testing**  
3. Add your Google account as tester; install from Play testing link  
4. Smoke: Google login, palm camera, free report, Razorpay/UPI (if testing payments)  
5. Promote to **Closed testing** (optional) → **Production** (India first)

First review often takes several days. Keep the upload keystore offline backup.

---

## After each update

1. Bump `versionCode` (+1) and `versionName` in `app/build.gradle`  
2. `./build_apk.ps1 -Bundle`  
3. Upload new AAB + release notes (what changed for users)  
4. Same upload keystore every time

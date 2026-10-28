# Property sharing

The mobile release adds a native share control in public property details and beside the saved-property heart. Before opening the share sheet, it re-fetches the listing using the existing anonymous public API, verifies matching ID and published status, then shares only title, formatted price, area and `https://patahao.app/p/<id>/`. It never shares auth tokens, exact addresses, owner/partner phone numbers or staff notes. Network errors do not produce a link. Native sheet failure offers copying the checked link. Duplicate taps are disabled and a source rectangle anchors the sheet for future iPad support. Native deep linking into an installed app is not included in this increment.

The website uses two narrow `_redirects` rules to forward `/p/<id>/` (and its no-slash variant) to Railway's `/p/<id>/`. The Django landing page is anonymous, read-only, server-rendered and mobile responsive. It projects only public fields and accepted photos. It includes escaped Open Graph metadata and a Google Play link. Recipients can read the property without installing or signing in; to request a viewing they use the existing app. Only currently published listings render; all other or missing records get the same generic 404, including for staff. Responses are private/no-store. Third-party messaging clients may retain old previews independently after a listing is removed; the actual page rechecks availability every time.

Deploy backend first, then website redirects. No database migrations are added. Mobile code is on `feature/mobile-property-sharing`, based on the tested mobile-partner-release branch so published legal and onboarding links remain intact. `share_plus` 13.3.1 supports Android and future iOS work; its documented requirements fit the existing Flutter 3.44.5, Dart 3.12.2, Java 17, AGP 9 and Kotlin toolchain. Refresh pubspec.lock and generated plugin registrations using the trusted local Flutter installation, never by hand.

## Local mobile verification

In PowerShell, fetch and switch to `feature/mobile-property-sharing` only after confirming there are no tracked local changes. Leave untracked backup files untouched. Inside mobile:

```powershell
flutter pub get
flutter analyze
flutter test
```

`mobile/test/property_share_test.dart` covers public payload privacy, unpublished records, fresh availability/metadata, native-sheet origin, duplicate-tap prevention, stale favourites, native failure/copy fallback and network errors. These Flutter tests must pass locally before building 27. Use a test property to share from details and saved properties to WhatsApp, open the received URL in a browser without signing in, then check copy-link and cancelled-sheet behavior. A native test must also confirm sharing does not accidentally open the saved card or remove the favourite.

Build 27 only after these checks. This source change does not update the app already in Google Play. iOS signing and App Store readiness remain separate work.

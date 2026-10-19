# Mobile partner recruitment entry

Built from feature/google-play-release in a separate feature/mobile-partner-entry
branch. The installed Play internal-testing app is not changed by this source
commit. Confirm the developer's current release checkout before integrating, as
local release changes and Play version overrides may not be committed here.

## Entry points

- Sign-up: below Create Account, without requiring customer registration.
- Login: below Create Account, before the account explanation.
- My Profile: permanent Become a Partner card in the profile list.

All entries use one widget and open https://patahao.app/become-a-partner/ in the
external browser. No customer credentials or user identifiers are sent in the
URL. Repeated taps are disabled during launch. Failure offers a selectable URL
and a Copy link action. The shared widget does not change customer registration,
account role, login or partner certification permissions.

## Required local verification

Run in the existing trusted developer Flutter environment. Cloud SDK setup was
previously blocked by automatic approval review after metadata endpoint access;
that setup was not retried. The source and widget tests have been reviewed, but
Flutter analysis, tests, lockfile refresh, Android build and device behavior are
not verified in the cloud workspace.

```bash
flutter pub get
flutter analyze
flutter test
```

Commit the resulting dependency lockfile and generated plugin registration
updates after reviewing them. Widget tests cover the destination, browser
failure, duplicate-launch prevention and profile entry. Check all three entry
points on an Android device, including a narrow display and larger text. Confirm
that the website accepts an application and produces a reference.

For the next signed app bundle, preserve app.patahao and the existing release
signing configuration. Select a version code higher than every previously
uploaded build for this app. Do not assume pubspec.yaml's current +24 is the
latest Play Console version; an earlier local build used an override. Build the
new bundle, upload it to the existing internal-testing track, and roll out that
release. Testers must install the update through Google Play. No production
release is part of this change.

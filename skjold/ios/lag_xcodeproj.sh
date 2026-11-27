#!/bin/sh
# Lager Skjold-App.xcodeproj (appen + widgets + Apple Watch) for signering og TestFlight.
#   sh lag_xcodeproj.sh <TEAM-ID> [build-nummer]
# TEAM-ID står på developer.apple.com/account under Membership (10 tegn). Krever XcodeGen: brew install xcodegen
set -e
cd "$(dirname "$0")"
[ -n "$1" ] || { echo "bruk: sh lag_xcodeproj.sh <TEAM-ID> [build-nummer]"; exit 1; }
command -v xcodegen >/dev/null || { echo "Installer XcodeGen først: brew install xcodegen"; exit 1; }
{
  echo "settings:"
  echo "  base:"
  echo "    DEVELOPMENT_TEAM: \"$1\""
  [ -n "$2" ] && echo "    CURRENT_PROJECT_VERSION: \"$2\""
} > team.yml
xcodegen generate --spec project.yml
echo "Ferdig: åpne Skjold-App.xcodeproj, velg «Any iOS Device (arm64)» og Product → Archive."

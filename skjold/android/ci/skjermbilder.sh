#!/usr/bin/env bash
# Kjøres inne i android-emulator-runner (se .github/workflows/android-skjermbilder.yml).
# Starter appen mot den falske Skjold-en på verten (10.0.2.2:8765) og tar bilde av hver fane + fullskjermspilleren.
set -u
PKG=no.kristo.skjold.app
ACT=no.kristo.skjold.MainActivity
HOST=10.0.2.2:8765
mkdir -p ut
adb install -r skjold/android/app/build/outputs/apk/debug/app-debug.apk
adb shell pm grant "$PKG" android.permission.POST_NOTIFICATIONS 2>/dev/null || true
adb shell settings put system screen_off_timeout 1800000 || true
# Ren statuslinje (demomodus)
adb shell settings put global sysui_demo_allowed 1 || true
adb shell am broadcast -a com.android.systemui.demo -e command enter >/dev/null || true
adb shell am broadcast -a com.android.systemui.demo -e command clock -e hhmm 1041 >/dev/null || true
adb shell am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false >/dev/null || true
adb shell am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4 >/dev/null || true
adb shell am broadcast -a com.android.systemui.demo -e command notifications -e visible false >/dev/null || true

skudd() {   # skudd <fil> <fane> [full]
  adb shell am force-stop "$PKG"
  local ekstra=""
  [ "${3:-}" = full ] && ekstra="--ez SkjoldDemoFull true"
  adb shell am start -n "$PKG/$ACT" --es SkjoldHost "$HOST" --ei SkjoldDemoTab "$2" $ekstra
  sleep 16
  adb exec-out screencap -p > "ut/$1.png"
  echo "tok ut/$1.png ($(stat -c %s "ut/$1.png") byte)"
}

skudd 1-hjem 0
skudd 2-lyd 1
skudd 3-rom 2
skudd 4-innstillinger 3
skudd 5-spiller 0 full
adb logcat -d -s AndroidRuntime:E | tail -n 30 || true
ls -la ut

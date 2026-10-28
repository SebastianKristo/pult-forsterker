#!/usr/bin/env bash
# KI Pultforsterker – USB-lydkort (UAC2) via configfs. Full speed (12 Mbit) slik at en ADuM3160/4160
# USB-isolator kan sitte mellom PC-en og forsterkeren. 48 kHz / 16 bit stereo = 1,5 Mbit – god margin.
set -e
G=/sys/kernel/config/usb_gadget/pultamp
modprobe libcomposite
if [ "$1" = "stop" ]; then
  [ -d "$G" ] && { echo "" > "$G/UDC" 2>/dev/null || true; rm -f "$G/configs/c.1/uac2.0"; rmdir "$G/configs/c.1/strings/0x409" "$G/configs/c.1" "$G/functions/uac2.0" "$G/strings/0x409" "$G" 2>/dev/null || true; }
  exit 0
fi
mkdir -p "$G"; cd "$G"
echo 0x1d6b > idVendor; echo 0x0104 > idProduct; echo 0x0100 > bcdDevice; echo 0x0200 > bcdUSB
echo full-speed > max_speed
mkdir -p strings/0x409
echo "KI-PULTAMP-0001" > strings/0x409/serialnumber; echo "Sebastian / KI" > strings/0x409/manufacturer; echo "Pultforsterker" > strings/0x409/product
mkdir -p configs/c.1/strings/0x409; echo "UAC2" > configs/c.1/strings/0x409/configuration; echo 250 > configs/c.1/MaxPower
mkdir -p functions/uac2.0
echo 48000 > functions/uac2.0/c_srate; echo 2 > functions/uac2.0/c_ssize; echo 3 > functions/uac2.0/c_chmask   # PC -> Pi: 48 kHz, 16 bit, stereo
echo 0 > functions/uac2.0/p_chmask                                                                             # ingen lyd fra Pi til PC
ln -sf functions/uac2.0 configs/c.1/
ls /sys/class/udc | head -1 > UDC

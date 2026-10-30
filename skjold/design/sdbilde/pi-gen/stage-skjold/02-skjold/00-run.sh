#!/bin/bash -e
# Skjold-programvaren: skjerm, knapper, web, oppsett
cp -r files/skjold "${ROOTFS_DIR}/opt/skjold"
install -d "${ROOTFS_DIR}/etc/skjold"
install -m 644 files/config.default.json "${ROOTFS_DIR}/etc/skjold/config.default.json"
for u in skjold-ui skjold-web skjold-setup skjold-improv skjold-update; do
  install -m 644 "files/systemd/${u}.service" "${ROOTFS_DIR}/etc/systemd/system/"
done
install -m 644 files/shairport-sync.conf "${ROOTFS_DIR}/etc/shairport-sync.conf"
install -m 644 files/skjold.service.avahi "${ROOTFS_DIR}/etc/avahi/services/skjold.service"
install -m 755 files/skjold-velkomst "${ROOTFS_DIR}/usr/local/bin/skjold-velkomst"
on_chroot << EOF
python3 -m venv /opt/skjold/venv
/opt/skjold/venv/bin/pip install -r /opt/skjold/requirements.txt
systemctl enable skjold-ui skjold-web skjold-setup skjold-improv skjold-update shairport-sync nqptp bluealsa avahi-daemon
EOF
# OLED (SSD1309 over SPI) og I2S-DAC
cat >> "${ROOTFS_DIR}/boot/firmware/config.txt" << EOF

# Skjold S1
dtparam=spi=on
dtparam=i2c_arm=on
dtparam=audio=off
dtoverlay=hifiberry-dacplus-std
EOF

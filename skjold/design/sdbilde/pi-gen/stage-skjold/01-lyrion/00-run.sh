#!/bin/bash -e
# Lyrion Music Server (tidligere Logitech Media Server) fra offisiell .deb
LYRION_DEB="lyrionmusicserver_9.0.0_arm.deb"
wget -q -O "${ROOTFS_DIR}/tmp/${LYRION_DEB}" "https://downloads.lms-community.org/LyrionMusicServer_v9.0.0/${LYRION_DEB}"
on_chroot << EOF
apt-get install -y /tmp/${LYRION_DEB}
rm /tmp/${LYRION_DEB}
systemctl enable lyrionmusicserver
EOF
# squeezelite spiller til ALSA-enheten 'skjold' (DAC på hovedkortet)
install -m 644 files/squeezelite.default "${ROOTFS_DIR}/etc/default/squeezelite"

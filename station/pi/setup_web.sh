#!/bin/bash
# Pi OS Bookworm (NetworkManager). Запуск: sudo bash setup_web.sh [пароль_wifi]
# 1) точка доступа STATION (10.42.0.1), если домашняя сеть не найдена; 2) автозапуск пульта на :8000.
set -e
PSK="${1:-station123}"; DIR="$(cd "$(dirname "$0")" && pwd)"; U="${SUDO_USER:-pi}"
hostnamectl set-hostname station
nmcli con delete STATION 2>/dev/null || true
nmcli con add type wifi ifname wlan0 con-name STATION ssid STATION autoconnect yes \
  connection.autoconnect-priority -10 802-11-wireless.mode ap 802-11-wireless.band bg \
  ipv4.method shared ipv4.addresses 10.42.0.1/24 wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
cat > /etc/systemd/system/station-web.service <<UNIT
[Unit]
Description=Station web panel
After=network.target
[Service]
User=$U
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/web.py --port 8000 --dir /home/$U/scans
Restart=always
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now station-web
echo "Готово. Wi-Fi STATION / $PSK -> http://10.42.0.1:8000 ; дома: http://station.local:8000"

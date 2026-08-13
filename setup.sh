#!/bin/bash
set -euo pipefail

# Prefer the active venv; fall back to common locations when run via sudo.
if [ -n "${VIRTUAL_ENV:-}" ]; then
  VENV_PATH="$VIRTUAL_ENV"
elif [ -n "${SUDO_USER:-}" ] && [ -d "/home/${SUDO_USER}/spotipi-venv" ]; then
  VENV_PATH="/home/${SUDO_USER}/spotipi-venv"
elif [ -d "${HOME}/spotipi-venv" ]; then
  VENV_PATH="${HOME}/spotipi-venv"
else
  echo "Enter the full path to your virtualenv (e.g. /home/kgary/spotipi-venv):"
  read -r VENV_PATH
fi

PIP="${VENV_PATH}/bin/pip"
PYTHON="${VENV_PATH}/bin/python"

if [ ! -x "$PIP" ] || [ ! -x "$PYTHON" ]; then
  echo "Virtualenv not found at: ${VENV_PATH}"
  echo "Create one first, e.g.:"
  echo "  python3 -m venv --system-site-packages ~/spotipi-venv"
  exit 1
fi

echo "Using virtualenv: ${VENV_PATH}"

run_as_owner() {
  if [ -n "${SUDO_USER:-}" ]; then
    sudo -u "$SUDO_USER" "$@"
  else
    "$@"
  fi
}

echo "Ensure packages are installed:"
sudo apt-get install -y libopenjp2-7 python3-dbus python3-venv python3-full

echo "Blacklist soundcard..."
echo "blacklist snd_bcm2835" | sudo tee /etc/modprobe.d/alsa-blacklist.conf >/dev/null

echo "Installing Python libraries into virtualenv:"
run_as_owner "$PIP" install spotipy==2.23.0 "pillow>=10.4.0" flask==3.0.0

echo "Enter your Spotify Client ID:"
read -r spotify_client_id

echo "Enter your Spotify Client Secret:"
read -r spotify_client_secret

echo "Enter your Spotify Redirect URI:"
read -r spotify_redirect_uri

echo "Enter your spotify username:"
read -r spotify_username

echo "Enter the full path to your Spotify token file (.cache)"
echo "Example: /home/${SUDO_USER:-$USER}/spotipy/spotipi/.cache"
read -r spotify_token_path

if [[ "$spotify_token_path" == http* ]] || [[ "$spotify_token_path" == *"code="* ]]; then
  echo "That looks like an OAuth redirect URL, not a file path."
  echo "Use the path to .cache instead, for example:"
  echo "  /home/${SUDO_USER:-$USER}/spotipy/spotipi/.cache"
  exit 1
fi

if [ ! -f "$spotify_token_path" ]; then
  echo "Token file not found: ${spotify_token_path}"
  echo "Run generate-token.sh first, then pass the full path to .cache"
  exit 1
fi

install_path=$(pwd)

echo "Installing Adafruit installer helper:"
run_as_owner "$PIP" install adafruit-python-shell

echo "Downloading rgb-matrix software setup:"
curl -fsSL https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.py >rgb-matrix.py

echo "Running rgb-matrix software setup (installs into your venv):"
# Keep venv on PATH so pip/python resolve correctly under sudo.
sudo -E env PATH="${VENV_PATH}/bin:$PATH" "$PYTHON" rgb-matrix.py

echo "Removing rgb-matrix setup script:"
rm -f rgb-matrix.py
echo "...done"

echo "Removing spotipi service if it exists:"
sudo systemctl stop spotipi || true
sudo rm -rf /etc/systemd/system/spotipi.service /etc/systemd/system/spotipi.service.d
sudo systemctl daemon-reload
echo "...done"

echo "Removing spotipi-client service if it exists:"
sudo systemctl stop spotipi-client || true
sudo rm -rf /etc/systemd/system/spotipi-client.service /etc/systemd/system/spotipi-client.service.d
sudo systemctl daemon-reload
echo "...done"

echo "Creating spotipi service:"
sudo cp ./config/spotipi.service /etc/systemd/system/
sudo sed -i -e "/\[Service\]/a ExecStart=${PYTHON} ${install_path}/python/displayCoverArt.py ${spotify_username} ${spotify_token_path}" /etc/systemd/system/spotipi.service
sudo mkdir -p /etc/systemd/system/spotipi.service.d
spotipi_env_path=/etc/systemd/system/spotipi.service.d/spotipi_env.conf
sudo tee "$spotipi_env_path" >/dev/null <<EOF
[Service]
Environment="SPOTIPY_CLIENT_ID=${spotify_client_id}"
Environment="SPOTIPY_CLIENT_SECRET=${spotify_client_secret}"
Environment="SPOTIPY_REDIRECT_URI=${spotify_redirect_uri}"
EOF
# Drop-in already sets Environment=; remove broken EnvironmentFile line from unit.
sudo sed -i '/^EnvironmentFile=/d' /etc/systemd/system/spotipi.service
sudo systemctl daemon-reload
sudo systemctl start spotipi
sudo systemctl enable spotipi
echo "...done"

echo "Creating spotipi-client service:"
sudo cp ./config/spotipi-client.service /etc/systemd/system/
sudo sed -i -e "/\[Service\]/a ExecStart=${PYTHON} ${install_path}/python/client/app.py" /etc/systemd/system/spotipi-client.service
sudo systemctl daemon-reload
sudo systemctl start spotipi-client
sudo systemctl enable spotipi-client
echo "...done"

echo -n "In order to finish setup a reboot is necessary..."
echo -n "REBOOT NOW? [y/N] "
read -r
if [[ ! "$REPLY" =~ ^(yes|y|Y)$ ]]; then
        echo "Exiting without reboot."
        exit 0
fi
echo "Reboot started..."
sudo reboot
sleep infinity

#!/bin/bash

POETRY_LOCATION=$(type -P -a poetry)
PROJECT_DIR=$(readlink -f "$(dirname -- "${BASH_SOURCE[0]}")/../..")

if [[ -z "${POETRY_LOCATION}" ]]
    echo "Poetry must be installed"
    exit 1
fi

mkdir -p ~/.config/systemd/user
cat <<EOF > ~/.config/systemd/user/twitfix.service
[Unit]
Description=Init file for twitfix uwsgi instance
After=network.target

[Service]
WorkingDirectory=${PROJECT_DIR}
Environment=TWITFIX_CONFIG_JSON=${PROJECT_DIR}/config.json
ExecStartPre=${POETRY_LOCATION} install --extra "deploy-here"
ExecStart=${POETRY_LOCATION} run uwsgi --ini twitfix.ini

[Install]
WantedBy=default.target
EOF
systemctl --user enable twitfix.service
systemctl --user start twitfix.service

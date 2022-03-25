#!/bin/bash

## Stops, disables, removes the users twitfix service.
systemctl --user stop twitfix.service
systemctl --user disable twitfix.service
rm ~/.config/systemd/user/twitfix.service

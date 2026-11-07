#!/bin/sh
# Watchdog: restart ebusd and/or the ebus logger (disptest.py) if they are not running.
# Run from pi's crontab:
#   0 * * * * /home/pi/check_disptest.sh
#   @reboot sleep 30 && /home/pi/check_disptest.sh

LOG=/home/pi/check_disptest.log
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }

# Anchored so it only matches the python process itself, not this script or cron's shell.
LOGGER='^python3 .*disptest\.py'

# 1. ebusd (systemd service). Needs passwordless sudo for pi.
if ! systemctl is-active --quiet ebusd; then
    sudo systemctl restart ebusd
    sleep 10
    if systemctl is-active --quiet ebusd; then
        log "ebusd not running - restarted"
    else
        log "ebusd not running - restart FAILED"
    fi
    # disptest.py holds a TCP connection to ebusd (port 8888) which is now dead,
    # so stop it and let step 2 start it again with a fresh connection.
    pkill -f "$LOGGER" && sleep 2
fi

# 2. The logger.
if ! pgrep -f "$LOGGER" > /dev/null; then
    cd /home/pi || exit 1
    setsid python3 disptest.py < /dev/zero > /dev/null 2>&1 &
    log "disptest.py not running - restarted"
fi

#!/usr/bin/env python3

import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(filename='/home/pi/cec_keepalive.log', level=logging.INFO)

def cec_command(cmd):
    subprocess.run(['cec-client', '-s', '-d', '1'], input=f"{cmd} 0\n".encode(), check=True)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
        print("Usage: cec_control.py [on|off]")
        sys.exit(1)

    cmd = sys.argv[1]
    action = "on" if cmd == "on" else "standby"
    cec_command(action)

    logging.info("Manual trigger: Display %s at %s", cmd.upper(), datetime.now().ctime())

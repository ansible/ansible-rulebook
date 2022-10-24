#!/usr/bin/env python
import csv
import datetime
import time

import psutil

# psutil truncates the name
name = "ansible-ruleboo"
interval = 30  # seconds

# get process
process = next(p for p in psutil.process_iter() if name in p.name())

now = datetime.datetime.now()
with open(f"{now.isoformat()}_results.csv", "w", newline="") as f:
    writer = csv.writer(f)
    # headers
    writer.writerow(["datetime", "bytes"])

    while True:
        now = datetime.datetime.now()
        writer.writerow([now, process.memory_info().rss])
        time.sleep(interval)

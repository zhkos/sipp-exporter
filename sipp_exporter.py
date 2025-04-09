#!/usr/bin/env python3

import os
import re
import csv
import glob
import time
import logging
import tempfile
import argparse
import subprocess
from functools import partial
from collections import namedtuple, deque
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


logger = logging.getLogger(__name__)

Metric = namedtuple("Metric", ["name", "value", "timestamp"])
MetricMetadata = namedtuple("MetricMetadata", ["prom_type", "factory"])


def header_name_to_metric(header: str) -> str:
    header = header.replace("(P)", "P").replace("(C)", "C")
    header = header.replace("<", "lt_").replace(">=", "ge_")
    header = re.sub('([a-z0-9])([A-Z])', r'\1_\2', header)
    header = re.sub('([A-Z])([A-Z][a-z])', r'\1_\2', header)
    return "sipp_" + header.lower()


class StatsReader(threading.Thread):

    __METADATA = {}
    METRICS_INFO = b""

    def __init__(self, stat_file):
        logger.debug(f"Init reader for {stat_file}")

        self.stat_file = open(stat_file, "r")
        self.reader = csv.reader(self.stat_file, delimiter=';')
        self.headers = [header_name_to_metric(hdr) for hdr in next(iter(self.reader)) if hdr]
        self.metrics = deque(maxlen=1000)
        self.off = threading.Event()

        super().__init__(name=f"{self.__class__.__name__}({stat_file})")

    def __iter__(self):
        while not self.off.is_set():
            yield from self.reader
            time.sleep(0.1)

    def get_or_init_metadata(self, name, value):
        if name not in self.__METADATA:

            # Deduct metric type
            if name.endswith("_p"):
                prom_type = "gauge"
            else:
                prom_type = "counter"

            # Deduct metric format
            if not value.isnumeric():
                if re.match(r"\d+:\d+:\d+:\d+", value):
                    def convert_microseconds_timer(time_str):
                        hours, minutes, seconds, microseconds = map(int, time_str.split(':'))
                        return (hours * 3600 + minutes * 60 + seconds) * 1000 + microseconds // 1000
                    factory = convert_microseconds_timer
                elif re.match(r"\d+:\d+:\d+", value):
                    def convert_seconds_timer(time_str):
                        hours, minutes, seconds = map(int, time_str.split(':'))
                        return (hours * 3600 + minutes * 60 + seconds) * 1000
                    factory = convert_seconds_timer
                else:
                    logger.error(f"Unexpected value for field {name}: '{value}'. Cannot parse as anything")
                    return None
            else:
                factory = lambda x: x

            StatsReader.__METADATA[name] = MetricMetadata(prom_type, factory)
            StatsReader.METRICS_INFO += f"# TYPE {name} {prom_type}\n".encode()

        return StatsReader.__METADATA[name]

    def run(self):
        logger.debug(f"Start reader for {self.stat_file.name}")

        for row in self:

            if not row:
                continue

            metrics = list(zip(self.headers, row))
            _, _, ts = metrics[2][1].split("\t")
            ts = int(float(ts))

            for name, value in metrics[3:]:
                if not value:
                    logger.debug(f"Field '{name}' contains empty value. Skipping...")
                    continue

                meta = self.get_or_init_metadata(name, value)

                if not meta:
                    logger.warning(f"No metadata for field '{name}' found. Skipping...")
                    continue

                self.metrics.append(Metric(name, meta.factory(value), ts))

    def join(self, timeout = None):
        self.off.set()
        super().join(timeout)
        self.stat_file.close()


class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self, readers, *args, **kwargs):
        self.readers = readers
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            self.wfile.write(StatsReader.METRICS_INFO)

            for reader in self.readers:
                while True:
                    try:
                        name, value, ts = reader.metrics.pop()
                        self.wfile.write(f"{name} {value} {ts}\n".encode())
                    except IndexError:
                        break

        else:
            self.send_response(404)
            self.end_headers()


def prepare_sipp_cmd(sipp_cmd: list):
    if len(sipp_cmd) < 2 or sipp_cmd[0] != '--' or sipp_cmd[1] != 'sipp':
        logger.error("Incorrect SIPp command")
        exit(1)

    sipp_cmd = sipp_cmd[1:]

    if "-trace_stat" not in sipp_cmd:
        logger.debug("-trace_stat was not provided for SIPp command. Adding automatically")
        sipp_cmd.insert(1, "-trace_stat")

    if "-stf" not in sipp_cmd:
        logger.debug("-stf was not provided for SIPp command. Temporary file will be generated")
        stat_file = tempfile.NamedTemporaryFile(delete_on_close=False, delete=False)
        stat_file.close()
        stat_file = stat_file.name
        sipp_cmd.insert(1, stat_file)
        sipp_cmd.insert(1, "-stf")
    else:
        stat_file = sipp_cmd[sipp_cmd.index("-stf") + 1]

    return sipp_cmd, stat_file



parser = argparse.ArgumentParser(description='SIPp metrics exporter. In counter names, (P) means Periodic - since last statistic row and (C) means Cumulated - since sipp was started.')
parser.add_argument('--filepath', type=str, help='Filename or wildcard for CSV stats')
parser.add_argument('--address', type=str, default=os.environ.get("SIPP_EXPORTER_ADDR", "127.0.0.1"),
                    help='Server address (default: 127.0.0.1) or env SIPP_EXPORTER_ADDR')
parser.add_argument('--port', type=int, default=os.environ.get("SIPP_EXPORTER_PORT", 8436),
                    help='Server port (default: 8436) or env SIPP_EXPORTER_PORT')


if __name__ == '__main__':
    readers = []
    sipp_proc = None
    args, sipp_cmd = parser.parse_known_args()

    if not args.filepath and not sipp_cmd:
        logger.error('Provide --filepath argument or SIPp launch command after "--"')
        exit(1)

    if sipp_cmd:
        sipp_cmd, stat_file = prepare_sipp_cmd(sipp_cmd)
        sipp_proc = subprocess.Popen(sipp_cmd)
        time.sleep(1)   # Let SIPp populate stat file first
        sipp_reader = StatsReader(stat_file)

    if args.filepath:
        for file in glob.glob(args.filepath):
            reader = StatsReader(file)
            readers.append(reader)

    for reader in readers:
        reader.start()

    server = HTTPServer((args.address, args.port), partial(RequestHandler, readers))

    try:
        server.serve_forever()
    finally:
        for reader in readers:
            reader.join()
        if sipp_proc:
            sipp_proc.kill()

#!/usr/bin/env python3

import os
import re
import csv
import argparse
from functools import partial
from collections import namedtuple, deque
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


Metric = namedtuple("Metric", ["name", "value", "timestamp"])
METRICS_Q = deque(maxlen=1000)
HEADERS = None


def header_name_to_metric(header: str) -> str:
    header = header.replace("(P)", "P").replace("(C)", "C")
    header = header.replace("<", "lt_").replace(">=", "ge_")
    header = re.sub('([a-z0-9])([A-Z])', r'\1_\2', header)
    header = re.sub('([A-Z])([A-Z][a-z])', r'\1_\2', header)
    return "sipp_" + header.lower()


class StatsReader(threading.Thread):
    def __init__(self, fp, *args, **kwargs):
        self.fp = fp
        self.reader = csv.reader(fp, delimiter=';')
        self.headers = [header_name_to_metric(hdr) for hdr in next(iter(self.reader)) if hdr]
        self.metrics = deque(maxlen=1000)
        self.off = threading.Event()

        super().__init__(*args, **kwargs)

    def __iter__(self):
        while not self.off.is_set():
            yield from self.reader

    def run(self):
        for row in self:
            if not row:
                continue

            metrics = list(zip(self.headers, row))
            _, _, ts = metrics[2][1].split("\t")
            ts = int(float(ts))

            for name, value in metrics[3:]:
                if value:
                    self.metrics.append(Metric(name, value, ts))

    def join(self, timeout = None):
        self.off.set()
        return super().join(timeout)


class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self, metrics, *args, **kwargs):
        self.metrics = metrics
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            # form http response
            while True:
                try:
                    name, value, ts = self.metrics.pop()
                    self.wfile.write(f"{name} {value} {ts}\n".encode())
                except IndexError:
                    break
        else:
            self.send_response(404)
            self.end_headers()


parser = argparse.ArgumentParser(description='SIPp metrics exporter. In counter names, (P) means Periodic - since last statistic row and (C) means Cumulated - since sipp was started.')
parser.add_argument('--file', type=str, default=os.getenv("SIPP_TRACE_STAT", '/var/log/sipp/sipp_trace_stat.log'),
                    help='Path to the CSV file (default: /var/log/sipp/sipp_trace_stat.log) or env SIPP_TRACE_STAT')
parser.add_argument('--address', type=str, default=os.environ.get("SIPP_EXPORTER_ADDR", "127.0.0.1"),
                    help='Server address (default: 127.0.0.1) or env SIPP_EXPORTER_ADDR')
parser.add_argument('--port', type=int, default=os.environ.get("SIPP_EXPORTER_PORT", 8436),
                    help='Server port (default: 8436) or env SIPP_EXPORTER_PORT')


if __name__ == '__main__':
    args = parser.parse_args()

    reader = StatsReader(open(args.file, "r"))
    reader.start()

    server = HTTPServer((args.address, args.port), partial(RequestHandler, reader.metrics))

    try:
        server.serve_forever()
    finally:
        reader.join()

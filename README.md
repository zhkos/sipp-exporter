# SIPp Exporter 📊

## 📝 Summary

Collects and exposes SIPp CSV statistics in Prometheus format.

Key features:
- 🚀 Runs alongside SIPp or processes existing stat files
- ⏱️ Converts SIPp's timing metrics to milliseconds
- 📈 Exposes metrics in Prometheus format
- 🏷️ Labeling metrics with stat filename
- 🔄 Handles both periodic (P) and cumulative (C) metrics
- 🌐 Simple web server for metric collection

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.6+
- SIPp installed

### Usage Options

#### Option 1: Run with SIPp command
```bash
./sipp_exporter.py --address 0.0.0.0 --port 8436 -- sipp -sn uac 192.168.1.100:5060
```

The exporter will:
1. Automatically add `-trace_stat` if missing
2. Create a temporary stats file if `-stf` isn't specified
3. Launch SIPp and collect its metrics

#### Option 2: Process existing stat files
```bash
./sipp_exporter.py --filepath /path/to/stats_*.csv --address 0.0.0.0 --port 8436
```

### Accessing Metrics
Metrics are available at:
```
http://<address>:<port>/metrics
```

### Environment Variables
You can also configure the server via environment variables:
```bash
export SIPP_EXPORTER_ADDR=0.0.0.0
export SIPP_EXPORTER_PORT=8436
./sipp_exporter.py -- sipp [options]
```

#!/usr/bin/env python3

import csv
import time
import os
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# global vars for metrics
metrics = {
    # 'sipp_start_time': 0,
    # 'sipp_last_reset_time': 0,
    # 'sipp_current_time': 0,
    # 'sipp_elapsed_time_p': 0,
    # 'sipp_elapsed_time_c': 0,
    'sipp_target_rate': 0,
    'sipp_call_rate_p': 0,
    'sipp_call_rate_c': 0,
    'sipp_incoming_call_p': 0,
    'sipp_incoming_call_c': 0,
    'sipp_outgoing_call_p': 0,
    'sipp_outgoing_call_c': 0,
    'sipp_total_call_created': 0,
    'sipp_current_call': 0,
    'sipp_successful_call_p': 0,
    'sipp_successful_call_c': 0,
    'sipp_failed_call_p': 0,
    'sipp_failed_call_c': 0,
    'sipp_failed_cannot_send_message_p': 0,
    'sipp_failed_cannot_send_message_c': 0,
    'sipp_failed_max_udp_retrans_p': 0,
    'sipp_failed_max_udp_retrans_c': 0,
    'sipp_failed_tcp_connect_p': 0,
    'sipp_failed_tcp_connect_c': 0,
    'sipp_failed_tcp_closed_p': 0,
    'sipp_failed_tcp_closed_c': 0,
    'sipp_failed_unexpected_message_p': 0,
    'sipp_failed_unexpected_message_c': 0,
    'sipp_failed_call_rejected_p': 0,
    'sipp_failed_call_rejected_c': 0,
    'sipp_failed_cmd_not_sent_p': 0,
    'sipp_failed_cmd_not_sent_c': 0,
    'sipp_failed_regexp_doesnt_match_p': 0,
    'sipp_failed_regexp_doesnt_match_c': 0,
    'sipp_failed_regexp_shouldnt_match_p': 0,
    'sipp_failed_regexp_shouldnt_match_c': 0,
    'sipp_failed_regexp_hdr_not_found_p': 0,
    'sipp_failed_regexp_hdr_not_found_c': 0,
    'sipp_failed_outbound_congestion_p': 0,
    'sipp_failed_outbound_congestion_c': 0,
    'sipp_failed_timeout_on_recv_p': 0,
    'sipp_failed_timeout_on_recv_c': 0,
    'sipp_failed_timeout_on_send_p': 0,
    'sipp_failed_timeout_on_send_c': 0,
    'sipp_failed_test_doesnt_match_p': 0,
    'sipp_failed_test_doesnt_match_c': 0,
    'sipp_failed_test_shouldnt_match_p': 0,
    'sipp_failed_test_shouldnt_match_c': 0,
    'sipp_failed_strcmp_doesnt_match_p': 0,
    'sipp_failed_strcmp_doesnt_match_c': 0,
    'sipp_failed_strcmp_shouldnt_match_p': 0,
    'sipp_failed_strcmp_shouldnt_match_c': 0,
    'sipp_out_of_call_msgs_p': 0,
    'sipp_out_of_call_msgs_c': 0,
    'sipp_dead_call_msgs_p': 0,
    'sipp_dead_call_msgs_c': 0,
    'sipp_retransmissions_p': 0,
    'sipp_retransmissions_c': 0,
    'sipp_auto_answered_p': 0,
    'sipp_auto_answered_c': 0,
    'sipp_warnings_p': 0,
    'sipp_warnings_c': 0,
    'sipp_fatal_errors_p': 0,
    'sipp_fatal_errors_c': 0,
    'sipp_watchdog_major_p': 0,
    'sipp_watchdog_major_c': 0,
    'sipp_watchdog_minor_p': 0,
    'sipp_watchdog_minor_c': 0,
    'sipp_response_time1_p': 0,
    'sipp_response_time1_c': 0,
    'sipp_response_time1_stdev_p': 0,
    'sipp_response_time1_stdev_c': 0,
    'sipp_call_length_p': 0,
    'sipp_call_length_c': 0,
    'sipp_call_length_stdev_p': 0,
    'sipp_call_length_stdev_c': 0,

    # # Repartition metrics
    # 'response_time_repartition_1': 0,
    # 'response_time_repartition_1_<10': 0,
    # 'response_time_repartition_1_<20': 0,
    # 'response_time_repartition_1_<30': 0,
    # 'response_time_repartition_1_<40': 0,
    # 'response_time_repartition_1_<50': 0,
    # 'response_time_repartition_1_<100': 0,
    # 'response_time_repartition_1_<150': 0,
    # 'response_time_repartition_1_<200': 0,
    # 'response_time_repartition_1_>=200': 0,

    # # Call length repartition metrics
    # 'call_length_repartition': 0,
    # 'call_length_repartition_<10': 0,
    # 'call_length_repartition_<50': 0,
    # 'call_length_repartition_<100': 0,
    # 'call_length_repartition_<500': 0,
    # 'call_length_repartition_<1000': 0,
    # 'call_length_repartition_<5000': 0,
    # 'call_length_repartition_<10000': 0,
    # 'call_length_repartition_>=10000': 0
}

# get env vars
file_path = os.getenv('SIPP_TRACE_STAT', '/var/log/sipp/sipp_trace_stat.log')
server_address = os.getenv('SIPP_EXPORTER_ADDR', '127.0.0.1')
server_port = int(os.getenv('SIPP_EXPORTER_PORT', 8436))

def read_last_row_from_csv(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return None

    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        last_row = None
        for row in reader:
            last_row = row  # save last string
    return last_row

def update_metrics(row):
    if row:
        # metrics['sipp_start_time'] = float(row[0])  # StartTime
        # metrics['sipp_last_reset_time'] = float(row[1])  # LastResetTime
        # metrics['sipp_current_time'] = float(row[2])  # CurrentTime
        # metrics['sipp_elapsed_time_p'] = float(row[3])  # ElapsedTime(P)
        # metrics['sipp_elapsed_time_c'] = float(row[4])  # ElapsedTime(C)
        metrics['sipp_target_rate'] = float(row[5])  # TargetRate
        metrics['sipp_call_rate_p'] = float(row[6])  # CallRate(P)
        metrics['sipp_call_rate_c'] = float(row[7])  # CallRate(C)
        metrics['sipp_incoming_call_p'] = float(row[8])  # IncomingCall(P)
        metrics['sipp_incoming_call_c'] = float(row[9])  # IncomingCall(C)
        metrics['sipp_outgoing_call_p'] = float(row[10])  # OutgoingCall(P)
        metrics['sipp_outgoing_call_c'] = float(row[11])  # OutgoingCall(C)
        metrics['sipp_total_call_created'] = float(row[12])  # TotalCallCreated
        metrics['sipp_current_call'] = float(row[13])  # CurrentCall
        metrics['sipp_successful_call_p'] = float(row[14])  # SuccessfulCall(P)
        metrics['sipp_successful_call_c'] = float(row[15])  # SuccessfulCall(C)
        metrics['sipp_failed_call_p'] = float(row[16])  # FailedCall(P)
        metrics['sipp_failed_call_c'] = float(row[17])  # FailedCall(C)
        metrics['sipp_failed_cannot_send_message_p'] = float(row[18])  # FailedCannotSendMessage(P)
        metrics['sipp_failed_cannot_send_message_c'] = float(row[19])  # FailedCannotSendMessage(C)
        metrics['sipp_failed_max_udp_retrans_p'] = float(row[20])  # FailedMaxUDPRetrans(P)
        metrics['sipp_failed_max_udp_retrans_c'] = float(row[21])  # FailedMaxUDPRetrans(C)
        metrics['sipp_failed_tcp_connect_p'] = float(row[22])  # FailedTcpConnect(P)
        metrics['sipp_failed_tcp_connect_c'] = float(row[23])  # FailedTcpConnect(C)
        metrics['sipp_failed_tcp_closed_p'] = float(row[24])  # FailedTcpClosed(P)
        metrics['sipp_failed_tcp_closed_c'] = float(row[25])  # FailedTcpClosed(C)
        metrics['sipp_failed_unexpected_message_p'] = float(row[26])  # FailedUnexpectedMessage(P)
        metrics['sipp_failed_unexpected_message_c'] = float(row[27])  # FailedUnexpectedMessage(C)
        metrics['sipp_failed_call_rejected_p'] = float(row[28])  # FailedCallRejected(P)
        metrics['sipp_failed_call_rejected_c'] = float(row[29])  # FailedCallRejected(C)
        metrics['sipp_failed_cmd_not_sent_p'] = float(row[30])  # FailedCmdNotSent(P)
        metrics['sipp_failed_cmd_not_sent_c'] = float(row[31])  # FailedCmdNotSent(C)
        metrics['sipp_failed_regexp_doesnt_match_p'] = float(row[32])  # FailedRegexpDoesntMatch(P)
        metrics['sipp_failed_regexp_doesnt_match_c'] = float(row[33])  # FailedRegexpDoesntMatch(C)
        metrics['sipp_failed_regexp_shouldnt_match_p'] = float(row[34])  # FailedRegexpShouldntMatch(P)
        metrics['sipp_failed_regexp_shouldnt_match_c'] = float(row[35])  # FailedRegexpShouldntMatch(C)
        metrics['sipp_failed_regexp_hdr_not_found_p'] = float(row[36])  # FailedRegexpHdrNotFound(P)
        metrics['sipp_failed_regexp_hdr_not_found_c'] = float(row[37])  # FailedRegexpHdrNotFound(C)
        metrics['sipp_failed_outbound_congestion_p'] = float(row[38])  # FailedOutboundCongestion(P)
        metrics['sipp_failed_outbound_congestion_c'] = float(row[39])  # FailedOutboundCongestion(C)
        metrics['sipp_failed_timeout_on_recv_p'] = float(row[40])  # FailedTimeoutOnRecv(P)
        metrics['sipp_failed_timeout_on_recv_c'] = float(row[41])  # FailedTimeoutOnRecv(C)
        metrics['sipp_failed_timeout_on_send_p'] = float(row[42])  # FailedTimeoutOnSend(P)
        metrics['sipp_failed_timeout_on_send_c'] = float(row[43])  # FailedTimeoutOnSend(C)
        metrics['sipp_failed_test_doesnt_match_p'] = float(row[44])  # FailedTestDoesntMatch(P)
        metrics['sipp_failed_test_doesnt_match_c'] = float(row[45])  # FailedTestDoesntMatch(C)
        metrics['sipp_failed_test_shouldnt_match_p'] = float(row[46])  # FailedTestShouldntMatch(P)
        metrics['sipp_failed_test_shouldnt_match_c'] = float(row[47])  # FailedTestShouldntMatch(C)
        metrics['sipp_failed_strcmp_doesnt_match_p'] = float(row[48])  # FailedStrcmpDoesntMatch(P)
        metrics['sipp_failed_strcmp_doesnt_match_c'] = float(row[49])  # FailedStrcmpDoesntMatch(C)
        metrics['sipp_failed_strcmp_shouldnt_match_p'] = float(row[50])  # FailedStrcmpShouldntMatch(P)
        metrics['sipp_failed_strcmp_shouldnt_match_c'] = float(row[51])  # FailedStrcmpShouldntMatch(C)
        metrics['sipp_out_of_call_msgs_p'] = float(row[52])  # OutOfCallMsgs(P)
        metrics['sipp_out_of_call_msgs_c'] = float(row[53])  # OutOfCallMsgs(C)
        metrics['sipp_dead_call_msgs_p'] = float(row[54])  # DeadCallMsgs(P)
        metrics['sipp_dead_call_msgs_c'] = float(row[55])  # DeadCallMsgs(C)
        metrics['sipp_retransmissions_p'] = float(row[56])  # Retransmissions(P)
        metrics['sipp_retransmissions_c'] = float(row[57])  # Retransmissions(C)
        metrics['sipp_auto_answered_p'] = float(row[58])  # AutoAnswered(P)
        metrics['sipp_auto_answered_c'] = float(row[59])  # AutoAnswered(C)
        metrics['sipp_warnings_p'] = float(row[60])  # Warnings(P)
        metrics['sipp_warnings_c'] = float(row[61])  # Warnings(C)
        metrics['sipp_fatal_errors_p'] = float(row[62])  # FatalErrors(P)
        metrics['sipp_fatal_errors_c'] = float(row[63])  # FatalErrors(C)
        metrics['sipp_watchdog_major_p'] = float(row[64])  # WatchdogMajor(P)
        metrics['sipp_watchdog_major_c'] = float(row[65])  # WatchdogMajor(C)
        metrics['sipp_watchdog_minor_p'] = float(row[66])  # WatchdogMinor(P)
        metrics['sipp_watchdog_minor_c'] = float(row[67])  # WatchdogMinor(C)
        # metrics['sipp_response_time1_p'] = float(row[68])  # ResponseTime1(P)
        # metrics['sipp_response_time1_c'] = float(row[69])  # ResponseTime1(C)
        # metrics['sipp_response_time1_stdev_p'] = float(row[70])  # ResponseTime1StDev(P)
        # metrics['sipp_response_time1_stdev_c'] = float(row[71])  # ResponseTime1StDev(C)
        # metrics['sipp_call_length_p'] = float(row[72])  # CallLength(P)
        # metrics['sipp_call_length_c'] = float(row[73])  # CallLength(C)
        # metrics['sipp_call_length_stdev_p'] = float(row[74])  # CallLengthStDev(P)
        # metrics['sipp_call_length_stdev_c'] = float(row[75])  # CallLengthStDev(C)

        # # Repartition metrics
        # metrics['response_time_repartition_1'] = row[76]  # ResponseTimeRepartition1
        # metrics['response_time_repartition_1_<10'] = row[77]  # ResponseTimeRepartition1_<10
        # metrics['response_time_repartition_1_<20'] = row[78]  # ResponseTimeRepartition1_<20
        # metrics['response_time_repartition_1_<30'] = row[79]  # ResponseTimeRepartition1_<30
        # metrics['response_time_repartition_1_<40'] = row[80]  # ResponseTimeRepartition1_<40
        # metrics['response_time_repartition_1_<50'] = row[81]  # ResponseTimeRepartition1_<50
        # metrics['response_time_repartition_1_<100'] = row[82]  # ResponseTimeRepartition1_<100
        # metrics['response_time_repartition_1_<150'] = row[83]  # ResponseTimeRepartition1_<150
        # metrics['response_time_repartition_1_<200'] = row[84]  # ResponseTimeRepartition1_<200
        # metrics['response_time_repartition_1_>=200'] = row[85]  # ResponseTimeRepartition1_>=200

        # # Call length repartition metrics
        # metrics['call_length_repartition'] = row[86]  # CallLengthRepartition
        # metrics['call_length_repartition_<10'] = row[87]  # CallLengthRepartition_<10
        # metrics['call_length_repartition_<50'] = row[88]  # CallLengthRepartition_<50
        # metrics['call_length_repartition_<100'] = row[89]  # CallLengthRepartition_<100
        # metrics['call_length_repartition_<500'] = row[90]  # CallLengthRepartition_<500
        # metrics['call_length_repartition_<1000'] = row[91]  # CallLengthRepartition_<1000
        # metrics['call_length_repartition_<5000'] = row[92]  # CallLengthRepartition_<5000
        # metrics['call_length_repartition_<10000'] = row[93]  # CallLengthRepartition_<10000
        # metrics['call_length_repartition_>=10000'] = row[94]  # CallLengthRepartition_>=10000

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            # form http response
            response = "\n".join(f"{key}: {value}" for key, value in metrics.items())
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server(address, port):
    server_address = (address, port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Server start at {address}:{port}")
    httpd.serve_forever()

def main():
    # start http server
    server_thread = threading.Thread(target=run_http_server, args=(server_address, server_port), daemon=True)
    server_thread.start()

    while True:
        last_row = read_last_row_from_csv(file_path)
        if last_row is not None:  # update metrics when files exists
            update_metrics(last_row)
        time.sleep(10)  # update metrics every 10 secs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SIPp metrics exporter. In counter names, (P) means Periodic - since last statistic row and (C) means Cumulated - since sipp was started.')
    parser.add_argument('--file', type=str, default=file_path, help='Path to the CSV file (default: /var/log/sipp/sipp_trace_stat.log) or env SIPP_TRACE_STAT')
    parser.add_argument('--address', type=str, default=server_address, help='Server address (default: 127.0.0.1) or env SIPP_EXPORTER_ADDR')
    parser.add_argument('--port', type=int, default=server_port, help='Server port (default: 8436) or env SIPP_EXPORTER_PORT')

    args = parser.parse_args()

    # Update global variables based on command line arguments
    file_path = args.file
    server_address = args.address
    server_port = args.port
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

import select
import socket
import time


NAGIOS_COMMAND_FILE = "/var/spool/nagios/cmd/nagios.cmd"
TELEGRAM_UNIX_SOCKET = "/var/spool/telegramd/telegramd.sock"
INTERVAL_DIALOGS_DISCOVER = 3  # second(s)
INTERVAL_OVERALL_CYCLE = 2  # second(s)


sock = None


def telegram_command(command):
    global sock
    sock.send(command + "\r\n")
    return sock.recv(4096)


def telegram_message(message, peer):
    return telegram_command("msg " + peer + " " + message)


def parseable(message):
    if len(message) == 0:
        return False
    message = message.replace("»»»", ">>>")
    if ">>>" not in message:
        return False
    return True


def command_ping():
    return "All right. I'm still here."


def command_ack(message):
    if message.lower()[:3] == "ack":
        message = message[3:].strip()
    if len(message) == 0 or message.lower() == "help":
        return "ack host_name [service_description]"
    else:
        params = message.split()
        hostname = params[0].replace("\"", "").replace("'", "")
        if len(params) > 1:
            service = " ".join(params[1:]).replace("\"", "").replace("'", "").strip()
            command = "[" + str(int(time.time())) + "] ACKNOWLEDGE_SVC_PROBLEM;" + hostname + ";" + service + ";1;1;1;nagiosadmin;Ack."
            return_message = "Service \"" + service + "\" on \"" + hostname + "\" acknowledgment correctly fired."
        else:
            command = "[" + str(int(time.time())) + "] ACKNOWLEDGE_HOST_PROBLEM;" + hostname + ";1;1;1;nagiosadmin;Ack."
            return_message = "Host \"" + hostname + "\" status acknowledgment correctly fired."
        nagios_command_file = open(NAGIOS_COMMAND_FILE, 'w')
        nagios_command_file.write(command + "\n")
        nagios_command_file.close()
        return return_message

while True:
    time.sleep(INTERVAL_OVERALL_CYCLE)
    if sock is None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(TELEGRAM_UNIX_SOCKET)
    try:
        ready_r, ready_w, ready_err = \
            select.select([sock, ], [sock, ], [], 5)
    except select.error:
        try:
            sock.shutdown(2)
            sock.close()
        except:
            pass
        finally:
            sock = None
        print "ERROR: " + str(e)
        continue

    unreads = set()
    for entry in telegram_command("dialog_list").split("\n"):
        if len(entry) > 0:
            if entry[:4].lower() == "user":
                splitter = "User"
            elif entry[:4].lower() == "chat":
                splitter = "Chat"
            else:
                continue
            peer = str(entry.split(":")[0].split(splitter)[1].strip().replace(" ", "_"))
            msgs = int(entry.split(":")[1].strip().split()[0])
            if msgs > 0:
                unreads.add(peer)
    time.sleep(INTERVAL_DIALOGS_DISCOVER)
    for peer in unreads:
        message_id = 0
        for line in telegram_command("history " + peer + " " + str(int((INTERVAL_DIALOGS_DISCOVER + INTERVAL_OVERALL_CYCLE) / 5))).split("\n"):
            message = line.replace("»»»", ">>>").strip()
            message_id += 1
            if parseable(message):
                message = message.split(">>>")[1].strip()
                if len(message) >= 4 and message.lower()[:4] == "ping":
                    telegram_message(command_ping(), peer)
                elif len(message) >= 3 and message.lower()[:3] == "ack":
                    telegram_message(command_ack(message), peer)
                else:
                    telegram_message("Command not found.", peer)

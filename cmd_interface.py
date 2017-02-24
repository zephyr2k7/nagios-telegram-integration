#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import time


NAGIOS_COMMAND_FILE = "/var/spool/nagios/cmd/nagios.cmd"
TELEGRAM_UNIX_SOCKET = "/var/spool/telegram-cli/telegram-cli.sock"
INTERVAL_DIALOGS_DISCOVER = 3  # second(s)
INTERVAL_OVERALL_CYCLE = 2  # second(s)


def parseable(message):
    if len(message) == 0:
        return False
    message = message.replace("»»»", ">>>")
    if ">>>" not in message:
        return False
    return True

sock = None

while True:
    if not sock:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(TELEGRAM_UNIX_SOCKET)
    try:
        # print "Getting dialog list"
        unreads = set()
        sock.send("dialog_list\r\n")
        for entry in sock.recv(2048).split("\n"):
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
        # print "Unread messages from: " + str(unreads) if len(unreads) > 0 else "No unread messages."
        time.sleep(INTERVAL_DIALOGS_DISCOVER)
        for peer in unreads:
            sock.send("history " + peer + " " + str(int((INTERVAL_DIALOGS_DISCOVER + INTERVAL_OVERALL_CYCLE) / 5)) + "\r\n")
            message_id = 0
            for line in sock.recv(4096).split("\n"):
                message = line.replace("»»»", ">>>").strip()
                message_id += 1
                # print "ID: " + str(message_id) + "\tLength: " + str(len(message)) + "\tStatus: " + ("kept" if parseable(message) else "ignored") + "\tBody: \"" + message + "\""
                if parseable(message):
                    message = message.split(">>>")[1].strip()
                    if message.lower() == "ping":
                        sock.send("msg " + peer + " All right. I'm still here.\r\n")
                        sock.recv(1024)
                    elif message.lower() == "ack help":
                        sock.send("msg " + peer + " Quick ACK syntax: \"ack host_name [service_description]\".\r\n")
                        sock.recv(1024)
                    else:
                        # print "ID: " + str(message_id) + "\tMessage: " + message
                        if "ack" in message.lower()[:3]:
                            params = message.split()
                            hostname = params[1].replace("\"", "").replace("'", "")
                            service = None
                            if len(params) > 2:
                                service = " ".join(params[2:]).replace("\"", "").replace("'", "").strip()
                            if service:
                                command = "[" + str(int(time.time())) + "] ACKNOWLEDGE_SVC_PROBLEM;" + hostname + ";" + service + ";1;1;1;nagiosadmin;Ack."
                                return_message = "Service \"" + service + "\" on \"" + hostname + "\" acknowledgment correctly fired."
                            else:
                                command = "[" + str(int(time.time())) + "] ACKNOWLEDGE_HOST_PROBLEM;" + hostname + ";1;1;1;nagiosadmin;Ack."
                                return_message = "Host \"" + hostname + "\" status acknowledgment correctly fired."
                            if command:
                                # print "ID: " + str(message_id) + "\tCommand: " + command
                                nagios_command_file = open(NAGIOS_COMMAND_FILE, 'w')
                                nagios_command_file.write(command + "\n")
                                nagios_command_file.close()
                                sock.send("msg " + peer + " " + return_message + "\r\n")
                                sock.recv(1024)
    except Exception as e:
        print "ERROR:" + str(e)
        try:
            sock.close()
        except:
            pass
        sock = None
    time.sleep(INTERVAL_OVERALL_CYCLE)

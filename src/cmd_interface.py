#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import select
import socket
import time


NAGIOS_COMMAND_FILE = "/var/spool/nagios/cmd/nagios.cmd"
NAGIOS_STATUS_FILE = "/var/log/nagios/status.dat"
TELEGRAM_UNIX_SOCKET = "/var/spool/telegramd/telegramd.sock"
INTERVAL_DIALOGS_DISCOVER = 3  # second(s)
INTERVAL_OVERALL_CYCLE = 2  # second(s)


sock = None
statuses = dict()
statuses_up = 0.0


def telegram_command(command):
    global sock
    sock.send(command + "\r\n")
    return sock.recv(4096)


def telegram_message(message, peer):
    for message_line in message.split("\n"):
        telegram_command("msg " + peer + " " + message_line)


def nagios_status_build():
    global statuses
    global statuses_up
    try:
        status_content = str()
        with open(NAGIOS_STATUS_FILE, 'r') as status_filename:
            status_content = status_filename.read()
    except Exception as e:
        print "ERROR: " + str(e)
        return
    statuses = dict()
    status_host = False
    status_host_name = str()
    status_srvc = False
    status_srvc_name = str()
    for line in status_content.split("\n"):
        if (status_host or status_srvc) and line.lower().strip() == "}":
            status_host = False
            status_srvc = False
        if status_host and "host_name" in line.lower():
            status_host_name = line.split("host_name=")[1].strip()
            statuses[status_host_name] = dict()
            statuses[status_host_name]["status"] = "UNKNOWN"
            statuses[status_host_name]["services"] = dict()
        elif status_host and line.lower().strip()[0:len("plugin_output")] == "plugin_output":
            statuses[status_host_name]["status"] = line.split("plugin_output=")[1].strip().split()[0]
        elif status_srvc and "host_name" in line.lower():
            status_host_name = line.split("host_name=")[1].strip()
        elif status_srvc and "service_description" in line.lower():
            status_srvc_name = line.split("service_description=")[1].strip()
            statuses[status_host_name]["services"][status_srvc_name] = "UNKNOWN"
        elif status_srvc and line.lower().strip()[0:len("plugin_output")] == "plugin_output":
            statuses[status_host_name]["services"][status_srvc_name] = line.split("plugin_output=")[1].strip()
        if "hoststatus" in line.lower():
            status_host = True
        elif "servicestatus" in line.lower():
            status_srvc = True
    statuses_up = os.path.getmtime(NAGIOS_STATUS_FILE)


def nagios_find_name(host, service=None):
    global statuses
    if service is None:
        for registered_host in statuses:
            if host.lower() == registered_host.lower()[:len(host)]:
                return registered_host
    else:
        for registered_srvc in statuses[host]["services"]:
            if service.lower() == registered_srvc.lower()[:len(service)]:
                return registered_srvc
    return None


def nagios_status(host, service=None):
    global statuses
    if service is None:
        return statuses[host]["status"]
    else:
        return statuses[host]["services"][service]
    return None


def parseable(message):
    if len(message) == 0:
        return False
    message = message.replace("»»»", ">>>")
    if ">>>" not in message:
        return False
    return True


def command_man():
    return "This interface is known to work with the following commands:\n - man\n - ping\n - ack\n - status\n - list\nFor any of those but \"man\" and \"ping\", you can use \"help\" option for assistance."


def command_ping():
    return "All right. I'm still here."


def command_ack(message):
    if message.lower()[:len("ack")] == "ack":
        message = message[len("ack"):].strip()
    if len(message) == 0 or message.lower() == "help":
        return "ack host_name [service_description]"
    else:
        params = message.split()
        hostname = nagios_find_name(params[0].replace("\"", "").replace("'", ""))
        if hostname is not None:
            if len(params) > 1:
                service = nagios_find_name(hostname, " ".join(params[1:]).replace("\"", "").replace("'", "").strip())
                if service is not None:
                    command = "[" + str(int(time.time())) + "] ACKNOWLEDGE_SVC_PROBLEM;" + hostname + ";" + service + ";1;1;1;nagiosadmin;Ack."
                    return_message = "Service \"" + service + "\" on \"" + hostname + "\" acknowledgment correctly fired."
                else:
                    return_message = "Service not found."
            else:
                command = "[" + str(int(time.time())) + "] ACKNOWLEDGE_HOST_PROBLEM;" + hostname + ";1;1;1;nagiosadmin;Ack."
                return_message = "Host \"" + hostname + "\" status acknowledgment correctly fired."
        else:
            return_message = "Host not found."
        nagios_command_file = open(NAGIOS_COMMAND_FILE, 'w')
        nagios_command_file.write(command + "\n")
        nagios_command_file.close()
        return return_message


def command_status(message):
    global statuses
    if message.lower()[:len("status")] == "status":
        message = message[len("status"):].strip()
    if message.lower() == "help":
        return "status [host_name [service_description]]"
    elif len(message) == 0:
        ret_statuses = str()
        nok_statuses = 0
        ok_statuses = 0
        for host in statuses:
            host_status = nagios_status(host)
            if host_status.lower() != "ok":
                nok_statuses += 1
                ret_statuses += " - Host \"" + host + "\" is " + str(host_status) + "\"\n"
            else:
                ok_statuses += 1
        if len(ret_statuses) > 0:
            ret_statuses = ret_statuses[:-2] + ". "
        ret_statuses += "\n" + (" - Other " if nok_statuses > 0 else str()) + str(ok_statuses) + " hosts are ok."
        return ret_statuses
    else:
        params = message.split()
        hostname = nagios_find_name(params[0].replace("\"", "").replace("'", ""))
        if hostname is not None:
            if len(params) > 1:
                service = nagios_find_name(hostname, " ".join(params[1:]).replace("\"", "").replace("'", "").strip())
                if service is not None:
                    status = nagios_status(hostname, service)
                    if status is not None:
                        return "Service \"" + service + "\" status  for \"" + hostname + "\" is: " + str(nagios_status(hostname, service))
                    else:
                        return "Service \"" + service + "\" for \"" + hostname + "\" not found."
                else:
                    return "Service not found."
            else:
                status_host = nagios_status(hostname)
                if status_host is not None:
                    status = "Host \"" + hostname + "\" overall status is: " + str(status_host)
                    for service in statuses[hostname]["services"]:
                        status += "\n - Service \"" + service + "\": " + statuses[hostname]["services"][service]
                    return status
                else:
                    return "Host \"" + hostname + "\" not found."
        else:
            return "Host not found."


def command_list(message):
    global statuses
    if message.lower()[:len("list")] == "list":
        message = message[len("list"):].strip()
    if message.lower() == "help":
        return "list [host_name]"
    elif len(message) == 0:
        ret_statuses = str()
        for host in statuses:
            ret_statuses += " - Host \"" + host + "\"\n"
        if len(ret_statuses) > 0:
            ret_statuses = ret_statuses[:-1]
        return ret_statuses
    else:
        params = message.split()
        hostname = nagios_find_name(params[0].replace("\"", "").replace("'", ""))
        if hostname is not None:
            status = "Host \"" + hostname + "\":\n"
            for service in statuses[hostname]["services"]:
                status += " - Service \"" + service + "\"\n"
            return status
        else:
            return "Host not found."

while True:
    if os.path.getmtime(NAGIOS_STATUS_FILE) > statuses_up:
        nagios_status_build()
    time.sleep(INTERVAL_OVERALL_CYCLE)
    if sock is None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(TELEGRAM_UNIX_SOCKET)
    try:
        ready_r, ready_w, ready_err = select.select([sock, ], [sock, ], [], 5)
    except select.error as e:
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
                if len(message) >= len("man") and message.lower()[:len("man")] == "man":
                    telegram_message(command_man(), peer)
                elif len(message) >= len("ping") and message.lower()[:len("ping")] == "ping":
                    telegram_message(command_ping(), peer)
                elif len(message) >= len("ack") and message.lower()[:len("ack")] == "ack":
                    telegram_message(command_ack(message), peer)
                elif len(message) >= len("status") and message.lower()[:len("status")] == "status":
                    telegram_message(command_status(message), peer)
                elif len(message) >= len("list") and message.lower()[:len("list")] == "list":
                    telegram_message(command_list(message), peer)
                else:
                    telegram_message("Command not found.", peer)

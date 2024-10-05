#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Service management tool
# Copyright (C) 2006-2011 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import os
import sys
import time
import comar
import dbus
import socket
import locale
import subprocess

# i18n

import gettext
__trans = gettext.translation('mudur', fallback=True)
_ = __trans.ugettext

# Utilities

def loadConfig(path):
    """Load configuration from the specified path."""
    d = {}
    with open(path) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value.startswith('"') or value.startswith("'"):
                    value = value[1:-1]
                d[key] = value
    return d

def waitBus(unix_name, timeout=10, wait=0.1, stream=True):
    """Wait for a D-Bus socket to become available."""
    sock_type = socket.SOCK_STREAM if stream else socket.SOCK_DGRAM
    sock = socket.socket(socket.AF_UNIX, sock_type)
    while timeout > 0:
        try:
            sock.connect(unix_name)
            return True
        except OSError:
            timeout -= wait
        time.sleep(wait)
    return False

# The main part of your program should go here, using the defined functions.

if __name__ == "__main__":
    # Example usage
    config_path = "/path/to/your/config.file"  # Update this with the actual config file path
    config = loadConfig(config_path)
    print(config)

    unix_socket_path = "/path/to/unix/socket"  # Update this with the actual socket path
    if waitBus(unix_socket_path):
        print(f"Successfully connected to the socket: {unix_socket_path}")
    else:
        print(f"Failed to connect to the socket: {unix_socket_path}")


# Operations

class Service:
    types = {
        "local": _("local"),
        "script": _("script"),
        "server": _("server"),
    }

    def __init__(self, name, info=None):
        self.name = name
        self.running = ""
        self.autostart = ""
        if info:
            servicetype, self.description, state = info
            self.state = state
            self.servicetype = self.types[servicetype]
            if state in ("on", "started", "conditional_started"):
                self.running = _("running")
            if state in ("on", "stopped"):
                self.autostart = _("yes")
            if state in ("conditional_started", "conditional_stopped"):
                self.autostart = _("conditional")


def format_service_list(services, use_color=True):
    """Format and print the list of services."""
    colors = {}
    if os.environ.get("TERM", "") == "xterm":
        colors = {
            "on": '[0;32m',
            "started": '[1;32m',
            "stopped": '[0;31m',
            "off": '[0m',
            "conditional_started": '[1;32m',
            "conditional_stopped": '[1;33m',
        }
    else:
        colors = {
            "on": '[1;32m',
            "started": '[0;32m',
            "stopped": '[1;31m',
            "off": '[0m',
            "conditional_started": '[0;32m',
            "conditional_stopped": '[0;33m',
        }

    run_title  = _("Status")
    name_title = _("Service")
    auto_title = _("Autostart")
    desc_title = _("Description")

    run_size  = max(max(map(lambda x: len(x.running), services)), len(run_title))
    name_size = max(max(map(lambda x: len(x.name), services)), len(name_title))
    auto_size = max(max(map(lambda x: len(x.autostart), services)), len(auto_title))
    desc_size = len(desc_title)

    line = "%s | %s | %s | %s" % (
        name_title.center(name_size),
        run_title.center(run_size),
        auto_title.center(auto_size),
        desc_title.center(desc_size)
    )
    print(line)
    print("-" * len(line))

    cend = "\x1b[0m"
    for service in services:
        cstart = "\x1b%s" % colors[service.state] if use_color else ""
        line = "%s%s%s | %s%s%s | %s%s%s | %s%s%s" % (
            cstart,
            service.name.ljust(name_size),
            cend, cstart,
            service.running.center(run_size),
            cend, cstart,
            service.autostart.center(auto_size),
            cend, cstart,
            service.description,
            cend
        )
        print(line)

def readyService(service):
    """Prepare the service to be started."""
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].ready()
    except dbus.DBusException as e:
        print(_("Unable to start %s:") % service)
        print("  %s" % e.args[0])

def startService(service, quiet=False):
    """Start the specified service."""
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].start()
    except dbus.DBusException as e:
        print(_("Unable to start %s:") % service)
        print("  %s" % e.args[0])
        return
    if not quiet:
        print(_("Starting %s") % service)

def stopService(service, quiet=False):
    """Stop the specified service."""
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].stop()
    except dbus.DBusException as e:
        print(_("Unable to stop %s:") % service)
        print("  %s" % e.args[0])
        return
    if not quiet:
        print(_("Stopping %s") % service)

def setServiceState(service, state, quiet=False):
    """Set the state of the specified service."""
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].setState(state)
    except dbus.DBusException as e:
        print(_("Unable to set %s state:") % service)
        print("  %s" % e.args[0])
        return
    if not quiet:
        if state == "on":
            print(_("Service '%s' will be auto started.") % service)
        elif state == "off":
            print(_("Service '%s' won't be auto started.") % service)
        else:
            print(_("Service '%s' will be started if required.") % service)

def reloadService(service, quiet=False):
    """Reload the specified service."""
    try:
        link = comar.Link()
        link.setLocale()
        link.useAgent(False)
        link.System.Service[service].reload()
    except dbus.DBusException as e:
        print(_("Unable to reload %s:") % service)
        print("  %s" % e.args[0])
        return
    if not quiet:
        print(_("Reloading %s") % service)

def getServiceInfo(service):
    """Retrieve information about the specified service."""
    link = comar.Link()
    link.setLocale()
    link.useAgent(False)
    return link.System.Service[service].info()

def getServices():
    """Get the list of available services."""
    link = comar.Link()
    link.setLocale()
    link.useAgent(False)
    return list(link.System.Service)

def list_services(use_color=True):
    """List all services and their status."""
    services = []
    for service in getServices():
        services.append((service, getServiceInfo(service), ))

    if services:
        services.sort(key=lambda x: x[0])
        service_objects = [Service(service, info) for service, info in services]
        format_service_list(service_objects, use_color)

def manage_service(service, op, use_color=True, quiet=False):
    """Manage a specific service based on the operation provided."""
    operations = {
        "ready": readyService,
        "start": startService,
        "stop": stopService,
        "reload": reloadService,
        "on": lambda s: setServiceState(s, "on", quiet),
        "off": lambda s: setServiceState(s, "off", quiet),
        "conditional": lambda s: setServiceState(s, "conditional", quiet),
        "info": lambda s: format_service_list([Service(service, getServiceInfo(service))], use_color),
        "status": lambda s: format_service_list([Service(service, getServiceInfo(service))], use_color),
        "list": lambda s: format_service_list([Service(service, getServiceInfo(service))], use_color),
        "restart": lambda s: (stopService(s, quiet), startService(s, quiet)),
    }

    if op in operations:
        operations[op](service)
    else:
        print(_("Invalid operation: %s") % op)

def run(*cmd):
    """Execute a command in the shell."""
    subprocess.call(cmd)

def manage_dbus(op, use_color, quiet):
    """Manage the D-Bus service."""
    if os.getuid() != 0 and op not in ["status", "info", "list"]:
        print(_("You must be root to use that."))
        return -1

    def cleanup():
        """Cleanup D-Bus PID and socket files."""
        for item in ["/run/dbus/pid", "/run/dbus/system_bus_socket"]:
            try:
                os.unlink(item)
            except OSError:
                pass

    if op == "start":
        if not quiet:
            print(_("Starting %s") % "DBus")
        cleanup()
        if not os.path.exists("/var/lib/dbus/machine-id"):
            run("/usr/bin/dbus-uuidgen", "--ensure")
        run("/sbin/start-stop-daemon", "-b", "--start", "--quiet",
            "--pidfile", "/run/dbus/pid", "--exec", "/usr/bin/dbus-daemon",
            "--", "--system")
        if not waitBus("/run/dbus/system_bus_socket", timeout=20):
            print(_("Unable to start DBus"))
            return -1
    elif op == "stop":
        if not quiet:
            print(_("Stopping %s") % "DBus")
        run("/sbin/start-stop-daemon", "--stop", "--quiet", "--pidfile", "/run/dbus/pid")
        cleanup()
    elif op == "restart":
        manage_dbus("stop", use_color, quiet)
        manage_dbus("start", use_color, quiet)
    elif op in ["info", "status", "list"]:
        try:
            dbus.SystemBus()
        except dbus.DBusException:
            print(_("DBus is not running."))
            return
        print(_("DBus is running."))



# Usage

def usage():
    """Print the usage information for the service command."""
    print(_("""usage: service [<options>] [<service>] <command>
where command is:
 list     Display service list
 status   Display service status
 info     Display service info
 on       Auto start the service
 off      Don't auto start the service
 start    Start the service
 stop     Stop the service
 restart  Stop the service, then start again
 reload   Reload the configuration (if service supports this)
and option is:
 -N, --no-color  Don't use color in output
 -q, --quiet     Don't print replies"""))

# Main
def main(args):
    operations = ("start", "stop", "info", "list", "restart", "reload", "status", "on", "off", "ready", "conditional")
    use_color = True
    quiet = False

    # Parameters
    if "--no-color" in args:
        args.remove("--no-color")
        use_color = False
    if "-N" in args:
        args.remove("-N")
        use_color = False
    if "--quiet" in args:
        args.remove("--quiet")
        quiet = True
    if "-q" in args:
        args.remove("-q")
        quiet = True

    # Operations
    if not args:
        list_services(use_color)
        return 0

    if args[0] == "list" and len(args) == 1:
        list_services(use_color)
        return 0

    if args[0] == "help":
        usage()
        return 0

    if len(args) < 2:
        usage()
        return 1

    if args[1] in operations and args[0] == "dbus":
        manage_dbus(args[1], use_color, quiet)
    elif args[1] in operations:
        try:
            manage_service(args[0].replace("-", "_"), args[1], use_color, quiet)
        except dbus.DBusException as e:
            if "Unable to find" in str(e):
                print(_("No such service: %s") % args[0])
            else:
                print("  %s" % e.args[0])
                return -1
        except ValueError as e:
            print(e)
            return -1
    else:
        usage()
        return 1

    return 0

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, '')
    sys.exit(main(sys.argv[1:]))

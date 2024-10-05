#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This file is part of free software (mudur); you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.

"""
Pisilinux system for creation, deletion and cleaning of volatile and temporary files.
"""

import os
import re
import sys
import stat
import shutil
from pwd import getpwnam
from grp import getgrnam

# Search files order
DEFAULT_CONFIG_DIRS_SO = ["/etc/tmpfiles.d", "/run/tmpfiles.d", "/usr/lib/tmpfiles.d"]
# Execution order
DEFAULT_CONFIG_DIRS_EO = ["/run/tmpfiles.d", "/usr/lib/tmpfiles.d", "/etc/tmpfiles.d"]

def read_file(path):
    """Read the content of a file."""
    with open(path) as f:
        return f.read().strip()

def write_file(path, content, mode="w"):
    """Write content to a file."""
    with open(path, mode) as f:
        f.write(content)

def create(file_type, path, mode, uid, gid, age, arg):
    """Create or manage files and directories based on the specified type."""
    if file_type == "d" and os.path.isdir(path) and (uid != os.stat(path).st_uid or gid != os.stat(path).st_gid):
        file_type = "D"

    if file_type == "L":
        if not os.path.islink(path):
            os.symlink(arg, path)
        return
    elif file_type == "D":
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.islink(path):
            os.remove(path)
    elif file_type == "c":
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            dev = [int(x) for x in arg.split(":")]
            os.mknod(path, mode | stat.S_IFCHR, os.makedev(dev[0], dev[1]))
            os.chown(path, uid, gid)

    if file_type.lower() == "d":
        if not os.path.isdir(path):
            os.makedirs(path, mode)
        os.chown(path, uid, gid)
    elif file_type in ["f", "F", "w"]:
        if not os.path.isfile(path) and file_type == "w":
            return
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.chown(os.path.dirname(path), uid, gid)
        write_file(path, arg, mode="a" if file_type == "f" else "w")
        os.chmod(path, mode)
        os.chown(path, uid, gid)

USAGE = """\
%s PATH(S)
\tparsing specified .conf files.
%s
\tparsing .conf files in:
\t%s
""" % (sys.argv[0], sys.argv[0], "; ".join(DEFAULT_CONFIG_DIRS_SO))

def usage():
    """Print usage information."""
    print(USAGE)
    sys.exit(0)

if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        usage()

    boot = "--boot" in sys.argv
    config_files = {}
    errors = []

    def add_config_file(head, tail):
        """Add a configuration file to the list."""
        try:
            config_files[head].append(tail)
        except KeyError:
            config_files[head] = [tail]

    if sys.argv[1:] and not boot:
        for arg in sys.argv[1:]:
            head, tail = os.path.split(arg)
            if not tail.endswith(".conf"):
                errors.append("%s is not a .conf file" % tail)
            elif not head:
                errors.append("Full path is needed for %s args." % sys.argv[0])
            elif not os.path.isdir(head):
                errors.append("Path %s does not exist." % head)
            elif not os.path.isfile(arg):
                errors.append("File %s does not exist." % arg)
            add_config_file(head, tail)
    else:
        all_files_names = []
        for head in DEFAULT_CONFIG_DIRS_SO:
            if not os.path.isdir(head):
                continue
            ls = os.listdir(head)
            for tail in ls:
                if not tail.endswith(".conf") or tail in all_files_names:
                    continue
                all_files_names.append(tail)
                add_config_file(head, tail)
            if ls and "baselayout.conf" in config_files[head]:
                config_files[head].insert(0, config_files[head].pop(config_files[head].index("baselayout.conf")))

    for d in DEFAULT_CONFIG_DIRS_EO:
        try:
            fs = config_files[d]
        except KeyError:
            continue
        for f in fs:
            conf = read_file(os.path.join(d, f))
            # Parse config file
            for line in [l for l in conf.split("\n") if l and not (l.startswith("#") or l.isspace())]:
                cerr = len(errors)
                fields = line.split()
                if len(fields) < 3:
                    errors.append("%s is invalid .conf file. Not enough args in line: %s" % (os.path.join(d, f), line))
                if len(fields) < 7:
                    fields.extend([""] * (7 - len(fields)))
                elif len(fields) > 7:
                    fields = fields[0:6] + [re.sub(".*?(%s)\\s*$" % "\\s+".join(fields[6:]), "\\1", line)]

                if fields[0] == "c" and not re.search("\\d+:\\d+", fields[6]):
                    errors.append("%s - wrong argument for type 'c' in file: %s" % (fields[6], os.path.join(d, f)))
                
                for n, i in enumerate(fields):
                    if i == "-":
                        fields[n] = ""
                if not fields[3]:
                    fields[3] = "root"
                if not fields[4]:
                    fields[4] = "root"
                if fields[0].endswith("!"):
                    if not boot:
                        continue
                    else:
                        fields[0] = fields[0].replace("!", "")
                if fields[0] not in ["c", "d", "D", "f", "F", "L", "w"]:
                    errors.append("%s - wrong type in file: %s" % (fields[0], os.path.join(d, f)))
                elif fields[0] == "L":
                    if not fields[6]:
                        errors.append("No arg for type 'L' specified in file: %s" % os.path.join(d, f))
                    elif not os.path.exists(fields[6]):
                        errors.append("%s - wrong path in file: %s" % (fields[6], os.path.join(d, f)))
                elif fields[0] in ["f", "F", "w"] and os.path.isdir(fields[1]):
                    errors.append("Cannot write to file. %s is a directory." % fields[1])
                else:
                    if not fields[2]:
                        errors.append("No mode specified in file: %s" % os.path.join(d, f))
                    elif not re.search("^\\d{3,4}$", fields[2]):
                        errors.append("%s - wrong mode in file: %s" % (fields[2], os.path.join(d, f)))
                    else:
                        fields[2] = int(fields[2], 8)
                    try:
                        fields[3] = getpwnam(fields[3]).pw_uid
                    except KeyError:
                        errors.append("User %s does not exist (%s)" % (fields[3], os.path.join(d, f)))
                    try:
                        fields[4] = getgrnam(fields[4]).gr_gid
                    except KeyError:
                        errors.append("Group %s does not exist (%s)" % (fields[4], os.path.join(d, f)))

                # Create files/directories as specified
                if len(errors) == cerr:
                    create(*fields)

    print("\n".join(errors))

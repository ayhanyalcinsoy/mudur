# -*- coding: utf-8 -*-
import os
import sys
import subprocess

def mountpoint(path):
    """Check if the given path is a mountpoint."""
    result = subprocess.run(["mountpoint", "-q", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

class Controller:
    def __init__(self, subsysname, hierarchy, num_cgroups, enabled):
        self.subsysname = subsysname
        self.hierarchy = hierarchy
        self.num_cgroups = num_cgroups
        self.enabled = enabled

    def mount(self):
        """Mount the cgroup if it is enabled."""
        if self.enabled == 1:
            os.chdir("/sys/fs/cgroup")
            if not mountpoint(self.subsysname):
                s = self.subsysname
                try:
                    os.makedirs(s, exist_ok=True)
                    result = subprocess.run(
                        ["mount", "-n", "-t", "cgroup", "-o", s, s],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    return result.returncode == 0
                except Exception as e:
                    print(f"Error mounting cgroup: {e}")
                    return False
        return True

class Cgroupfs:
    def __init__(self):
        self.controllers = {}
        if self.check_fstab():
            print("cgroupfs in fstab, exiting.")
            sys.exit(-1)

        if not self.kernel_support():
            print("No kernel support for cgroupfs, exiting.")
            sys.exit(-2)

        if not self.check_sysfs():
            print("/sys/fs/cgroup directory not found, exiting")
            sys.exit(-3)

        self.mount_cgroup()
        self.find_controllers()
        for cname, c in self.controllers.items():
            c.mount()

    def check_fstab(self):
        """Check if cgroup is present in fstab."""
        found = False
        with open("/etc/fstab") as fstab:
            for line in fstab:
                if line.startswith("#"):
                    continue
                if "cgroup" in line:
                    found = True
                    break
        return found

    def kernel_support(self):
        """Check if the kernel supports cgroups."""
        return os.path.isfile("/proc/cgroups")

    def check_sysfs(self):
        """Check if the /sys/fs/cgroup directory exists."""
        return os.path.isdir("/sys/fs/cgroup")

    def mount_cgroup(self):
        """Mount the cgroup filesystem if not already mounted."""
        if not mountpoint("/sys/fs/cgroup"):
            cmd = "mount -t tmpfs -o uid=0,gid=0,mode=0755 cgroup /sys/fs/cgroup"
            return os.system(cmd)

    def find_controllers(self):
        """Read /proc/cgroups and find all controllers."""
        with open("/proc/cgroups") as cgroups:
            for line in cgroups:
                line = line.strip()
                if line.startswith("#"):
                    continue
                subsysname, hierarchy, num_cgroups, enabled = line.split()
                enb = int(enabled)
                hie = int(hierarchy)
                numc = int(num_cgroups)
                self.controllers[subsysname] = Controller(subsysname, hie, numc, enb)

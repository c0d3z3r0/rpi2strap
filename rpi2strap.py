#!/usr/bin/env python3

__author__ = "Michael Niewöhner"

import os
import sys
import time
import re
import argparse
import subprocess as su
import colorama as co
import tempfile as tm
import shutil as sh


def logwrite(text):
    log = open("rpi2strap.log", "a")
    log.write(text + "\n")
    log.close()


def lprint(p):
    print(p)
    logwrite(p)


def print_err(error):
    lprint(co.Fore.RED + """\
***********************************************
* Error! Please check the following messages! *
*         Your system will NOT boot!          *
***********************************************

""" + error + "\n")


def print_warn(warning):
    lprint(co.Fore.YELLOW + warning + co.Fore.RESET)


def run(command, out=0, quit=1):
    if out:
        ret = su.call(command, shell=True)
        success = not ret
        error = "Unknown error."
    else:
        ret = su.getstatusoutput(command)
        success = not ret[0]
        error = ret[1]
        logwrite(error + "\n")

    if quit and not success:
        print_err(error)
        try:
            sys.exit(1)
        except OSError:
            pass
    else:
        return success


def parseargs():
    parser = argparse.ArgumentParser(description='RPi2strap')
    parser.add_argument('--oc', "-o", action="store_true",
                        help='enable overclocking')
    parser.add_argument('sdcard', nargs=1,
                        help='sd card to install debian on e.g. /dev/sdc')
    return parser.parse_args()


def checkdep():
    tools = [("mkfs.msdos", "dosfstools"),
             ("cdebootstrap", "cdebootstrap"),
             ("curl", "curl"),
             ("fdisk", "fdisk"),
             ("sed", "sed"),
             ("qemu-arm-static", "qemu-arm-static"),
             ("fuser", "psmisc"),
             ]
    missing = []
    for t in tools:
        run("which %s" % t[0], quit=0) or missing.append(t[1])
    if missing:
        print_err("Missing dependencies: %s" % ', '.join(missing))


def main():
    co.init()
    args = parseargs()

    logwrite("\n\n" + time.strftime("%c"))

    if os.geteuid():
        print_err("You need to run RPi2strap as root!")
        sys.exit(1)

    sdcard = args.sdcard[0]
    if not re.match("^/dev/[a-zA-Z]+$", sdcard):
        print_err("Wrong sdcard format! Should be /dev/sdX.")
        sys.exit(1)

    if not os.path.exists(sdcard):
        print_err("SD card path does not exist.")
        sys.exit(1)

    lprint("Welcome to rpi2strap!")

    lprint(co.Fore.RED + "This is your last chance to abort!" + co.Fore.RESET)
    print_warn("Your sdcard is %s. Is that right? [yN] " % sdcard)
    if input() is not "y":
        lprint("OK. Aborting ...")
        sys.exit(0)

    run("umount -f %s*" % sdcard, quit=0)

    # Delete MBR and partition table and create a new one
    lprint("Delete MBR and partition table and create a new one.")
    run("dd if=/dev/zero of=%s bs=1M count=1" % sdcard)
    run("(echo o; echo n; echo p; echo 1; echo ; echo +32M; echo t; "
        "echo e; echo n; echo p; echo 2; echo ; echo ; echo w) | "
        "fdisk %s" % sdcard)

    # Create filesystems and mount them
    lprint("Create filesystems and mount them.")
    run("mkfs.msdos %s1" % sdcard)
    run("mkfs.ext4 -F %s2" % sdcard)
    tmp = tm.TemporaryDirectory()
    run("mount %s2 %s" % (sdcard, tmp.name))

    # Ok, let's install debian
    lprint("Install debian. First stage. This will take some minutes.")
    packages = ["aptitude", "apt-transport-https", "openssh-server",
                "cpufrequtils", "cpufreqd", "ntp", "fake-hwclock", "tzdata",
                "locales", "console-setup", "console-data", "vim", "psmisc",
                "keyboard-configuration", "ca-certificates"
                ]
    run("cdebootstrap --arch=armhf -f standard --foreign jessie "
        "--include=%s %s" % (','.join(packages), tmp.name))

    # Run second stage installer
    lprint("Second stage. Again, please wait some minutes.")
    print_warn("You can safely ignore the perl and locale warnings.")
    sh.copy2("/usr/bin/qemu-arm-static", "%s/usr/bin/qemu-arm-static"
             % tmp.name)
    run("chroot %s /sbin/cdebootstrap-foreign" % tmp.name)
    run("chroot %s dpkg-reconfigure locales console-setup console-data "
        "keyboard-configuration tzdata" % tmp.name, out=1)

    # Write config files
    lprint("Configure the system.")

    # fstab
    f = open("%s/etc/fstab" % tmp.name, "w")
    print("""\
proc            /proc           proc    defaults          0       0
/dev/mmcblk0p1  /boot           vfat    defaults          0       2
/dev/mmcblk0p2  /               ext4    defaults,noatime  0       1
# a swapfile is not a swap partition, so no using swapon|off from here on,
# use  dphys-swapfile swap[on|off]  for that""", file=f)
    f.close()

    # Networking
    f = open("%s/etc/network/interfaces" % tmp.name, "w")
    print("""\
auto eth0
iface eth0 inet dhcp""", file=f)
    f.close()

    # Hostname
    f = open("%s/etc/hostname" % tmp.name, "w")
    print("raspberrypi", file=f)
    f.close()

    # Add apt sources
    f = open("%s/etc/apt/sources.list" % tmp.name, "w")
    print("""\
deb http://ftp.de.debian.org/debian/ jessie main contrib non-free
deb-src http://ftp.de.debian.org/debian/ jessie main contrib non-free

deb http://security.debian.org/ jessie/updates main contrib non-free
deb-src http://security.debian.org/ jessie/updates main contrib non-free

deb http://ftp.de.debian.org/debian jessie-updates main contrib non-free
deb-src http://ftp.de.debian.org/debian jessie-updates main contrib non-free

deb http://ftp.de.debian.org/debian jessie-proposed-updates main contrib non-free
deb-src http://ftp.de.debian.org/debian jessie-proposed-updates main contrib non-free

deb http://ftp.debian.org/debian/ jessie-backports main contrib non-free
deb-src http://ftp.debian.org/debian/ jessie-backports main contrib non-free

deb http://archive.raspberrypi.org/debian wheezy main
deb-src http://archive.raspberrypi.org/debian wheezy main""", file=f)
    f.close()

    # APT settings
    f = open("%s/etc/apt/apt.conf.d/01debian" % tmp.name, "w")
    print("""\
APT::Default-Release "jessie";
aptitude::UI::Package-Display-Format "%c%a%M%S %p %Z %v %V %t";""", file=f)
    f.close()

    # APT pinning
    f = open("%s/etc/apt/preferences.d/aptpinning" % tmp.name, "w")
    print("""\
Package: *
Pin: release n=jessie-backports
Pin-Priority: 100

Package: *
Pin: origin archive.raspberrypi.org
Pin-Priority: 100""", file=f)
    f.close()

    # Change DHCP timeout because we get stuck at boot if there is no network
    run("sed -i'' 's/#timeout.*;/timeout 10;/' %s/etc/dhcp/dhclient.conf"
        % tmp.name)

    # Enable SSH PasswordAuthentication and root login
    run("sed -i'' 's/without-password/yes/' %s/etc/ssh/sshd_config"
        % tmp.name)
    run("sed -i'' 's/#PasswordAuth/PasswordAuth/' %s/etc/ssh/sshd_config"
        % tmp.name)

    # Set up default root password
    run("chroot %s echo 'root:toor' | chpasswd" % tmp.name)

    # Update & Upgrade
    lprint("Update the system.")
    run("chroot %s apt-key adv --fetch-keys http://archive.raspberrypi.org/"
        "debian/raspberrypi.gpg.key" % tmp.name)
    run("chroot %s aptitude -y update" % tmp.name)
    run("chroot %s aptitude -y upgrade" % tmp.name)

    # Install rpi-update and raspi-config package
    lprint("Install rpi-update and raspi-config package.")
    run("chroot %s aptitude -t wheezy -y install rpi-update raspi-config"
        % tmp.name)
    run("chroot %s systemctl disable raspi-config.service" % tmp.name)

    # Install kernel and modules
    lprint("Install kernel and modules.")
    run("mount %s1 %s/boot" % (sdcard, tmp.name))
    os.mkdir("%s/lib/modules" % tmp.name, 755)
    run("chroot %s /usr/bin/rpi-update" % tmp.name)

    # Link videocore binaries
    f = open("%s/etc/ld.so.conf.d/videocore.conf" % tmp.name, "w")
    print("/opt/vc/lib", file=f)
    f.close()
    run("chroot %s ldconfig" % tmp.name)
    for item in os.listdir('%s/opt/vc/bin' % tmp.name):
        os.symlink('%s/opt/vc/bin/' % tmp.name + item,
                   "%s/usr/bin/" % tmp.name + item)
    for item in os.listdir('%s/opt/vc/sbin' % tmp.name):
        os.symlink('%s/opt/vc/sbin/' % tmp.name + item,
                   "%s/usr/sbin/" % tmp.name + item)

    # Add cmdline and config to boot partition
    lprint("Add cmdline.")
    f = open("%s/boot/cmdline.txt" % tmp.name, "w")
    print("dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 "
          "root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline rootwait",
          file=f)
    f.close()

    # Overclocking
    if args.oc:
        lprint("Configure overclocking.")
        f = open("%s/boot/config.txt" % tmp.name, "w")
        print("""\
#disable_overscan=1
#hdmi_group=2
#hdmi_mode=82
#hdmi_drive=1
#hdmi_force_hotplug=1
#config_hdmi_boost=5
arm_freq=1050
gpu_freq=250
sdram_freq=550
over_voltage=6
over_voltage_sdram=6
core_freq=550
avoid_pwm_pll=1
gpu_mem=16
disable_splash=1
init_emmc_clock=300000000""", file=f)
        f.close()

    # Unmount and cleanup
    lprint("Unmount and cleanup.")
    run("fuser -k %s/boot %s/* %s" % (tmp.name, tmp.name, tmp.name))
    run("umount %s1" % sdcard, quit=0)
    run("umount %s2" % sdcard, quit=0)
    run("umount -f %s1" % sdcard, quit=0)
    run("umount -f %s2" % sdcard, quit=0)
    tmp.cleanup()

    lprint(co.Fore.GREEN + "OK, that's it. Put the sdcard into your rpi2 and "
                           "power it up.\nThe root password is 'toor'."
                         + co.Fore.RESET)


if __name__ == '__main__':
    main()
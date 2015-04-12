#!/usr/bin/env python3

__author__ = "Michael Niewöhner"

import os
import sys
import time
import re
import argparse
import subprocess as su
import colorama as co
import tempfile


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
    lprint(co.Fore.YELLOW + warning)


def run(command, check=1, quit=1, err=1):
    ret = su.getstatusoutput(command)
    logwrite(ret[1] + "\n")
    if check and ret[0]:
        if err:
            print_err(ret[1])
        if quit:
            sys.exit(1)
        else:
            return False
    else:
        return True


def parseargs():
    parser = argparse.ArgumentParser(description='RPi2strap')
    parser.add_argument('--oc', "-o", action="store_true",
                        help='enable overclocking')
    parser.add_argument('sdcard', nargs=1,
                        help='sd card to install debian on e.g. /dev/sdc')
    return parser.parse_args()


def checkdep():
    tools = [("dosfstools", "mkfs.msdos"),
             ("cdebootstrap", "cdebootstrap"),
             ("curl", "curl"),
             ("csplit", "csplit"),
             ("fdisk", "fdisk"),
             ("sed", "sed"),
             ("mktemp", "mktemp")
             ]
    missing = []
    for t in tools:
        run("which %s" % t[1], quit=0, err=0) or missing.append(t[0])
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
    print_warn("Note that you will need to enter your root password when "
               "you are prompted for a password.")

    lprint(co.Fore.RED + "This is your last chance to abort!")
    print_warn("Your sdcard is %s. Is that right? [yN] " % sdcard)
    if input() is not "y":
        lprint("OK. Aborting ...")
        sys.exit(0)

    run("umount -f %s*" % sdcard, check=0)

    # Delete MBR and partition table and create a new one
    lprint("Deleting MBR and partition table and create a new one.")
    run("dd if=/dev/zero of=%s bs=1M count=1" % sdcard)
    run("(echo o; echo n; echo p; echo 1; echo ; echo +32M; echo t; "
        "echo e; echo n; echo p; echo 2; echo ; echo ; echo w) | "
        "fdisk %s" % sdcard)

    # Create filesystems and mount them
    lprint("Creating filesystems and mount them.")
    tmp = tempfile.TemporaryDirectory()
    os.mkdir("%s/boot" % tmp.name, 755)
    os.mkdir("%s/root" % tmp.name, 755)
    run("mkfs.msdos %s1" % sdcard)
    run("mkfs.ext4 %s2" % sdcard)
    run("mount %s1 %s/boot" % (sdcard, tmp.name))
    run("mount %s2 %s/root" % (sdcard, tmp.name))

    # Ok, let's install debian
    lprint("Ok, let's install debian. This can take some minutes.")
    packages = ["aptitude", "apt-transport-https", "openssh-server",
                "cpufrequtils", "cpufreqd", "ntp", "fake-hwclock", "tzdata",
                "locales", "console-setup", "console-data", "vim", "psmisc",
                "keyboard-configuration", "ca-certificates"
                ]
    run("cdebootstrap --arch=armhf -f standard --foreign jessie "
        "--include=%s %s/root" % (','.join(packages), tmp.name))

    # Install kernel and modules
    lprint("Installing kernel and modules.")
    run("curl -o %s/root/usr/bin/rpi-update https://raw.githubusercontent.com/"
        "Hexxeh/rpi-update/master/rpi-update" % tmp.name)
    os.chmod("%s/root/usr/bin/rpi-update" % tmp.name, 755)
    os.mkdir("%s/root/lib/modules" % tmp.name, 755)
    run("ROOT_PATH=%s/root BOOT_PATH=%s/boot %s/root/usr/bin/rpi-update"
        % (tmp.name, tmp.name, tmp.name))

    # Add cmdline and config to boot partition
    lprint("Adding cmdline and config to boot partition.")
    f = open("%s/boot/cmdline.txt" % tmp.name, "w")
    print("dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 "
          "root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline rootwait",
          file=f)
    f.close()

    # Overclocking
    if args.oc:
        f = open("%s/boot/config.txt" % tmp.name, "w")
        print("""\
disable_overscan=1
hdmi_group=2
hdmi_mode=35
hdmi_drive=1
hdmi_force_hotplug=1
config_hdmi_boost=5
arm_freq=1050
gpu_freq=250
sdram_freq=550
over_voltage=6
over_voltage_sdram=6
core_freq=550
avoid_pwm_pll=1
gpu_mem=16
disable_splash=1
init_emmc_clock=300000000""",
              file=f)
        f.close()

    # Fix init script to mount rootfs writeable
    lprint("Fixing init script to mount rootfs writeable.")
    run("sed -i'' 's/rootfs/\/dev\/mmcblk0p2/' %s/root/sbin/init" % tmp.name)

    # fstab
    lprint("Writing fstab.")
    f = open("%s/root/etc/fstab" % tmp.name, "w")
    print("""\
proc            /proc           proc    defaults          0       0
/dev/mmcblk0p1  /boot           vfat    defaults          0       2
/dev/mmcblk0p2  /               ext4    defaults,noatime  0       1
# a swapfile is not a swap partition, so no using swapon|off from here on,
# use  dphys-swapfile swap[on|off]  for that,""",
          file=f)
    f.close()

    # Networking
    lprint("Setting up networking and hostname.")
    f = open("%s/root/etc/network/interfaces" % tmp.name, "w")
    print("""\
auto eth0
iface eth0 inet dhcp""",
          file=f)
    f.close()

    # Hostname
    f = open("%s/root/etc/hostname" % tmp.name, "w")
    print("raspberrypi", file=f)
    f.close()

    # Adding some things to the first boot´s init script
    lprint("Adding more instructions to the first boot´s init script.")
    o = open("%s/root/sbin/init" % tmp.name, "r")
    olines = o.readlines()
    o.close()
    nlines = """\
# Set up default root password
echo "root:toor" | chpasswd

# Add apt sources - we CANNOT do this before second stage finished!
cat <<"EOF" >/etc/apt/sources.list
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
deb-src http://archive.raspberrypi.org/debian wheezy main
EOF

# APT settings
cat <<"EOF" >/etc/apt/apt.conf.d/01debian
APT::Default-Release "jessie";
aptitude::UI::Package-Display-Format "%c%a%M%S %p %Z %v %V %t";
EOF

# APT pinning
cat <<"EOF" >/etc/apt/preferences.d/aptpinning
Package: *
Pin: release n=jessie-backports
Pin-Priority: 100

Package: *
Pin: origin archive.raspberrypi.org
Pin-Priority: 100
EOF

# Update & Upgrade
run ifconfig eth0 up
run dhclient -v eth0
echo "Aptitude error that jessie isn't a valid source can be safely ignored."
run apt-key adv --fetch-keys http://archive.raspberrypi.org/debian/raspberrypi.gpg.key
run aptitude -y update
run aptitude -y upgrade

# Install rpi-update and raspi-config package
run aptitude -t wheezy -y install rpi-update raspi-config
# Disable raspi-config init script because we have cpufreqd
run update-rc.d -f raspi-config remove

# Change DHCP timeout because we get stuck at boot if there is no network
sed -i'' 's/#timeout.*;/timeout 10;/' /etc/dhcp/dhclient.conf

# Enable SSH PasswordAuthentication and root login
sed -i'' 's/without-password/yes/' /etc/ssh/sshd_config
sed -i'' 's/#PasswordAuth/PasswordAuth/' /etc/ssh/sshd_config

# Reconfigure some packages
export DEBIAN_FRONTEND=dialog
run dpkg-reconfigure locales console-setup console-data keyboard-configuration tzdata

# Link videocore binaries
echo /opt/vc/lib >/etc/ld.so.conf.d/videocore.conf
ldconfig

# Add videocore binaries to PATH for root
ln -s /opt/vc/bin/* /usr/bin/
ln -s /opt/vc/sbin/* /usr/sbin/

# Add reboot to rc.local as a workaround to reboot because we need init
cp /etc/rc.local /etc/rc.local.ORIG
cat <<"EOF" >/etc/rc.local
#!/bin/sh
mv /etc/rc.local.ORIG /etc/rc.local
reboot
exit 0
EOF""".splitlines()

    npos = len(olines)-1
    olines[npos:npos] = nlines
    n = open("%s/root/sbin/init" % tmp.name, "w")
    n.writelines(nlines)
    n.close()

    # Unmount and cleanup
    lprint("Unmount and cleanup.")
    run("umount %s*" % sdcard, check=0)
    time.sleep(5)
    run("umount -f %s*" % sdcard, check=0)
    tmp.cleanup()

    lprint(co.Fore.GREEN + "OK, that's it. Plug in Network, HDMI and keyboard,"
                           " put the sdcard in your rpi2 and power it up.")


if __name__ == '__main__':
    main()
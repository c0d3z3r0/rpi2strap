#!/usr/bin/env python3

__author__ = 'Michael Niewöhner <c0d3z3r0>'
__email__ = 'mniewoeh@stud.hs-offenburg.de'

import argparse
import sys
import os

# TODO: move argparse to armdebootstrap
def parseargs():
    parser = argparse.ArgumentParser(description='RPi2strap')
    parser.add_argument('sdcard', nargs=1,
                        help='SD card to install debian on e.g. /dev/sdc')
    parser.add_argument('--packages', "-p",
                        help='Comma separated list of additional packages')
    parser.add_argument('--boot-size', "-b", type=int, default = 100,
                        help='Boot partition size in MB')
    parser.add_argument('--debug', "-d", action="store_true",
                        help='Enable debug output')
    return parser.parse_args()


def main():
    args = parseargs()
    name = 'RPi2strap'
    hostname = 'raspberrypi'
    bootsize = '+' + str(args.boot_size) + 'M'
    partitions = [
        {'start': '', 'end': bootsize, 'type': 'e', 'fs': 'msdos',
         'mount': '/boot'},
        {'start': '', 'end': '', 'type': '83', 'fs': 'ext4',
         'mount': '/'}
    ]
    packages = ["fake-hwclock", "binutils", "whiptail", "parted", "lua5.1",
                "triggerhappy"]
    if args.packages:
        packages += args.packages.split(',')

    # Download latest armdebootstrap
    if not os.path.isfile("armdebootstrap.py"):
        os.system('curl -so armdebootstrap.py --connect-timeout 5 '
                  'https://raw.githubusercontent.com/c0d3z3r0/armdebootstrap/'
                  'master/armdebootstrap.py')

    # Initialize ArmDebootstrap and start the installation process
    from armdebootstrap import ArmDeboostrap
    adb = ArmDeboostrap(name, hostname, args.sdcard[0], partitions,
                        packages, debug=args.debug)
    adb.init()
    adb.install()

    # ################### RPi specific stuff ####################

    # Install rpi-update and raspi-config package
    adb.lprint("Install rpi-update and raspi-config package.")
    adb.run('curl -Lso %s/usr/bin/rpi-update '
            'https://raw.githubusercontent.com/Hexxeh/rpi-update/master/'
            'rpi-update' % adb.tmp)
    adb.run('curl -Lso %s/usr/bin/raspi-config '
            'https://raw.githubusercontent.com/c0d3z3r0/raspi-config/workbench/'
            'raspi-config' % adb.tmp)
    adb.run('chmod +x %s/usr/bin/rpi-update %s/usr/bin/raspi-config' %
            (adb.tmp, adb.tmp))

    # Install kernel and modules
    adb.lprint("Install kernel and modules.")
    if not os.path.isdir("%s/lib/modules" % adb.tmp):
        os.mkdir("%s/lib/modules" % adb.tmp, 755)
    adb.run("SKIP_WARNING=1 chroot %s /usr/bin/rpi-update" % adb.tmp)

    # Add videocore binaries to path
    adb.writeFile('/etc/ld.so.conf.d/videocore.conf', '/opt/vc/lib')
    adb.run("chroot %s ldconfig" % adb.tmp)
    adb.writeFile('/etc/profile.d/paths.sh',
                  'export PATH="${PATH}:/opt/vc/sbin:/opt/vc/bin"')

    # Add cmdline and config to boot partition
    adb.lprint("Add cmdline.")
    adb.writeFile('/boot/cmdline.txt',
                  "dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 "
                  "root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline "
                  "rootwait")

    # touch /boot/config
    adb.writeFile('/boot/config.txt', "")

    # ################### end RPi specific stuff ####################

    adb.cleanup()
    sys.exit(0)


if __name__ == '__main__':
    main()
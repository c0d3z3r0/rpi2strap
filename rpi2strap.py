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
    parser.add_argument('--oc', "-o", action="store_true",
                        help='Enable overclocking')
    return parser.parse_args()


def main():

    args = parseargs()
    name = 'RPi2strap'
    hostname = 'raspberrypi'
    sdcard = args.sdcard[0]
    partitions = [
        {'start': '', 'end': '+32M', 'type': 'e', 'fs': 'msdos',
         'mount': '/boot'},
        {'start': '', 'end': '', 'type': '83', 'fs': 'ext4',
         'mount': '/'}
    ]
    packages = ["fake-hwclock"]
    if args.packages:
        packages += args.packages.split(',')

    # Download latest armdebootstrap and create object
    os.system('curl -so armdebootstrap.py --connect-timeout 5 '
              'https://raw.githubusercontent.com/c0d3z3r0/armdebootstrap/'
              'master/armdebootstrap.py')
    from armdebootstrap import ArmDeboostrap
    adb = ArmDeboostrap(name, hostname, sdcard, partitions, packages)

    # Initialize ArmDebootstrap and start the installation process
    adb.init()
    adb.install()

    # ################### RPi specific stuff ####################

    # Install rpi-update and raspi-config package
    adb.lprint("Install rpi-update and raspi-config package.")
    adb.run("chroot %s aptitude -t wheezy -y install rpi-update raspi-config"
            % adb.tmp.name)
    adb.run("chroot %s systemctl disable raspi-config.service" % adb.tmp.name)

    # Install kernel and modules
    adb.lprint("Install kernel and modules.")
    os.mkdir("%s/lib/modules" % adb.tmp.name, 755)
    adb.run("chroot %s /usr/bin/rpi-update" % adb.tmp.name)

    # Link videocore binaries
    adb.writeFile('/etc/ld.so.conf.d/videocore.conf', '/opt/vc/lib')
    adb.run("chroot %s ldconfig" % adb.tmp.name)
    for item in os.listdir('%s/opt/vc/bin' % adb.tmp.name):
        os.symlink('%s/opt/vc/bin/' % adb.tmp.name + item,
                   "%s/usr/bin/" % adb.tmp.name + item)
    for item in os.listdir('%s/opt/vc/sbin' % adb.tmp.name):
        os.symlink('%s/opt/vc/sbin/' % adb.tmp.name + item,
                   "%s/usr/sbin/" % adb.tmp.name + item)

    # Add cmdline and config to boot partition
    adb.lprint("Add cmdline.")
    adb.writeFile('/boot/cmdline.txt',
                  "dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 "
                  "root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline "
                  "rootwait")

    # Overclocking
    if args.oc:
        adb.lprint("Configure overclocking.")
        adb.writeFile('/boot/config.txt', """\
#disable_overscan=1
#hdmi_group=2
#hdmi_mode=82
#hdmi_drive=1
#hdmi_force_hotplug=1
#config_hdmi_boost=5
core_freq=550
gpu_freq=250
arm_freq=1050
over_voltage=6
sdram_freq=550
over_voltage_sdram=6
init_emmc_clock=300000000
avoid_pwm_pll=1
gpu_mem=32
disable_splash=1\
        """)
    else:
        # touch /boot/config
        open('/boot/config.txt', 'w').close()

    # ################### end RPi specific stuff ####################

    adb.cleanup()
    sys.exit(0)


if __name__ == '__main__':
    main()

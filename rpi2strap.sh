#!/bin/bash
# Author: Michael Niewöhner (c0d3z3r0)
# https://github.com/c0d3z3r0/rpi2strap

echo Welcome to rpi2strap!

[ `id -u` ne 0 ] && echo Run as root with sudo! && exit 1

( [ "$1" == "" ] || [ ! -e "$1" ] ) && \
				echo Please specify your sdcard. && \
				echo e.g. ./rpi2strap.sh /dev/sdc && \
				exit 1

[ ! -e /sbin/mkfs.msdos ] && echo Please install dosfstools && exit 1
#[ ! -e /usr/bin/qemu-arm-static ] && echo Please install qemu-user-static && exit 1
[ ! -e /usr/bin/cdebootstrap ] && echo Please install cdebootstrap && exit 1
[ ! -e /usr/bin/curl ] && echo Please install curl && exit 1

# Set up temp environment
tmpdir=$(mktemp -d)
sdcard=$(echo $1 | sed 's/[0-9]*$//')
mkdir $tmpdir/{boot,root}
umount -f ${sdcard}* 2>/dev/null

# Last warning ;-)
echo This is your last chance to abort this.
read -p "Your sdcard is $sdcard. Is that right? [y] " ok
[ "$ok" != "y" ] && echo "Ok, abort." && exit 1

# First let's download some files we need later
curl -o $tmpdir/root/usr/bin/rpi-update https://raw.githubusercontent.com/Hexxeh/rpi-update/master/rpi-update
chmod +x $tmpdir/root/usr/bin/rpi-update

# Delete MBR with dd because fdisk doesn't work sometimes
dd if=/dev/zero of=$sdcard bs=1M count=1

# Create partitions on SDcard
echo "o\nx\nh\n4\ns\n16\nr\nn\np\n1\n\n+30M\nt\ne\nn\np\n2\n\n\nw\n" | fdisk $sdcard
(echo o; echo n; echo p; echo 1; echo ; echo +32M; echo t; echo e; echo n; echo p; echo 2; echo ; echo ; echo w) | fdisk $sdcard

sync;sync;sync
mkfs.msdos ${sdcard}1
mkfs.ext4 ${sdcard}2
mount ${sdcard}1 $tmpdir/boot
mount ${sdcard}2 $tmpdir/root

# Ok, let's install debian jessie
cdebootstrap --arch=armhf -f standard --foreign jessie --include=openssh-server,cpufrequtils,cpufreqd,ntp,fake-hwclock,tzdata,locales,keyboard-configuration $tmpdir/root

# Install kernel and modules
mkdir $tmpdir/root/lib/modules
ROOT_PATH=$tmpdir/root BOOT_PATH=$tmpdir/boot $tmpdir/root/usr/bin/rpi-update

# Add cmdline and config to boot partition
cat <<"EOF" >$tmpdir/boot/cmdline.txt
dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline rootwait
EOF

cat <<"EOF" >$tmpdir/boot/config.txt
disable_overscan=1
hdmi_group=2
hdmi_mode=35
hdmi_drive=1
hdmi_force_hotplug=1
config_hdmi_boost=5
arm_freq=1050
gpu_freq=250
sdram_freq=530
over_voltage=6
over_voltage_sdram=4
core_freq=550
avoid_pwm_pll=1
gpu_mem=16
disable_splash=1
init_emmc_clock=250000000
EOF

# Fix init script to mount rootfs writeable
sed -i'' 's/rootfs/\/dev\/mmcblk0p2/' $tmpdir/root/sbin/init

# fstab
cat <<"EOF" >$tmpdir/root/etc/fstab
proc            /proc           proc    defaults          0       0
/dev/mmcblk0p5  /boot           vfat    defaults          0       2
/dev/mmcblk0p6  /               ext4    defaults,noatime  0       1
# a swapfile is not a swap partition, so no using swapon|off from here on, use  dphys-swapfile swap[on|off]  for that
EOF

# Network
cat <<"EOF" >$tmpdir/root/etc/network/interfaces
auto eth0
iface eth0 inet dhcp
EOF

#set up root password
#apt sources +rpi
#Some more stuff here...

#Unmount
umount ${sdcard}*
sleep 3
umount -f ${sdcard}*

echo OK, that\'s it. Just put the sdcard in your rpi2.

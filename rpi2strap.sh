#!/bin/bash
# Author: Michael Niewöhner (c0d3z3r0)
# https://github.com/c0d3z3r0/rpi2strap

echo Welcome to rpi2strap!

# Some basic checks here
[ `id -u` -ne 0 ] && echo Run as root with sudo! && exit 1

( [ "$1" == "" ] || [ ! -e "$1" ] ) && \
	echo Please specify your sdcard. && \
	echo e.g. ./rpi2strap.sh /dev/sdc && \
	exit 1

[ ! -e /sbin/mkfs.msdos ] && echo Please install dosfstools && exit 1
[ ! -e /usr/bin/cdebootstrap ] && echo Please install cdebootstrap && exit 1
[ ! -e /usr/bin/curl ] && echo Please install curl && exit 1

# Set up temp environment
tmpdir=$(mktemp -d)
sdcard=$(echo $1 | sed 's/[0-9]*$//')
cd $tmpdir
mkdir $tmpdir/{boot,root}
umount -f ${sdcard}* 2>/dev/null

# Last warning ;-)
echo This is your last chance to abort this.
read -p "Your sdcard is $sdcard. Is that right? [y] " ok
[ "$ok" != "y" ] && echo "Ok, abort." && exit 1

# Delete MBR with dd because fdisk doesn't work sometimes
dd if=/dev/zero of=$sdcard bs=1M count=1

# Create partitions on SDcard
(echo o; echo n; echo p; echo 1; echo ; echo +32M; echo t; echo e; echo n;
 echo p; echo 2; echo ; echo ; echo w) | fdisk $sdcard

sync;sync;sync
mkfs.msdos ${sdcard}1
mkfs.ext4 ${sdcard}2
mount ${sdcard}1 $tmpdir/boot
mount ${sdcard}2 $tmpdir/root

# Ok, let's install debian jessie
cdebootstrap --arch=armhf -f standard --foreign jessie --include=aptitude,apt-transport-https,openssh-server,cpufrequtils,cpufreqd,ntp,fake-hwclock,tzdata,locales,console-setup,console-data,keyboard-configuration,ca-certificates,vim,psmisc $tmpdir/root

# Install kernel and modules
curl -o $tmpdir/root/usr/bin/rpi-update https://raw.githubusercontent.com/Hexxeh/rpi-update/master/rpi-update
chmod +x $tmpdir/root/usr/bin/rpi-update
mkdir $tmpdir/root/lib/modules
ROOT_PATH=$tmpdir/root BOOT_PATH=$tmpdir/boot $tmpdir/root/usr/bin/rpi-update

# Add cmdline and config to boot partition
cat <<-"EOF" >$tmpdir/boot/cmdline.txt
	dwc_otg.lpm_enable=0 console=ttyAMA0,115200 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline rootwait
EOF

if [ "$1" != "-d" ]; then
	cat <<-"EOF" >$tmpdir/boot/config.txt
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
	init_emmc_clock=300000000
	EOF
fi

# Fix init script to mount rootfs writeable
sed -i'' 's/rootfs/\/dev\/mmcblk0p2/' $tmpdir/root/sbin/init

# fstab
cat <<-"EOF" >$tmpdir/root/etc/fstab
	proc            /proc           proc    defaults          0       0
	/dev/mmcblk0p1  /boot           vfat    defaults          0       2
	/dev/mmcblk0p2  /               ext4    defaults,noatime  0       1
	# a swapfile is not a swap partition, so no using swapon|off from here on,
	# use  dphys-swapfile swap[on|off]  for that
EOF

# Network
cat <<-"EOF" >$tmpdir/root/etc/network/interfaces
	auto eth0
	iface eth0 inet dhcp
EOF

# Hostname
echo raspberrypi >$tmpdir/root/etc/hostname

# Adding some things to the first boot´s init script
csplit -f init $tmpdir/root/sbin/init '/echo.*deb.*sources\.list/'
cat init00 >$tmpdir/root/sbin/init
cat <<-"EOT" >>$tmpdir/root/sbin/init
	# Set up default root password
	echo "root:toor" | chpasswd
	
	# Add apt sources - we CANNOT do this before second stage finished!
	cat <<-"EOF" >/etc/apt/sources.list
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
	cat <<-"EOF" >/etc/apt/apt.conf.d/01debian
		APT::Default-Release "jessie";
		aptitude::UI::Package-Display-Format "%c%a%M%S %p %Z %v %V %t";
	EOF
	
	# APT pinning
		cat <<-"EOF" >/etc/apt/preferences.d/aptpinning
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
	cat <<-"EOF" >/etc/rc.local
		#!/bin/sh
		mv /etc/rc.local.ORIG /etc/rc.local
		reboot
		exit 0
	EOF
EOT
tail -n +2 init01 >>$tmpdir/root/sbin/init

# Unmount
umount ${sdcard}*
sleep 3
umount -f ${sdcard}*

echo OK, that\'s it. Plug in Network HDMI and keyboard, put the sdcard in \
		 your rpi2 and power it up.

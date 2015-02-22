# rpi2strap for Raspberry Pi 2

## What is it?
rpi2strap is a script for installing Debian GNU/Linux Jessie 8.0 armhf to a sd card. You will get real Debian, not Raspbian!

## Why?
Why not? :-) I *hate* downloading big sd card images and dd'ing them onto my sd cards resulting in an overblown Raspbian installation with software I would never use. You'll simply get a basic Debian installation like from the netinstaller with some more basic packages (see below). Additionally you can use more recent software and get Debian security updates faster.

## What you will need and how to I use it
There is some software you have to install: grep, curl, csplit, dosfstools and cdebootstrap. You need an ethernet connection. **The installer does not work with wifi!**

./rpi2strap /dev/[your sdcard]
Follow the instructions. After this first stage plug in ethernet, HDMI and a keyboard and power up your Raspberry Pi 2. The installation will continue and after a reboot you can login with root:toor.

## Packages already included
- debian standard packages
- keyboard-configuration, console-data, console-setup
- ntp, tzdata, locales, openssh-server, ca-certificates, openssl
- cpufrequtils, cpufreqd, rpi-update, raspi-config
- vim

## I need some Raspbian packages like raspi-config!
No problem! The raspberrypi.org repository is now included in the sources.list. If you need packages from there like gpio you have to select them manually in aptitude. They will *never* be installed by dependecy because we **don't want to mix them up** with Debian packages. We just want to use the repo for some specific packages. Btw. raspi-config and rpi-update are already included so please don't install them with aptitude.

## I want wheezy instead of jessie
Open the script with vim and type `:%s/jessie/wheezy`. Then close vim with `:wq`. That's it.

## Warnings
rpi2strap is only working for Raspberry Pi 2. Every prior versions like B or B+ are **NOT SUPPORTED!** This is because pi2 is armv7 while earlier boards have armv6 which isn't supported by Debian armhf.

Please check that the config.txt (look inside my script) fits your needs. It has HDMI/DVI and overclocking enabled. Graphics memory is set to the smallest possible value because I only use it as a server.

The installer enables SSH root login and password authentication so you can easily ssh to your new Debian installation. For security reasons you shouldn't use that in an production environment. Switch to pubkey authentication instead.


## Am I allowed to modify and share it?
Yes, of course but please keep the author name where it is :-)

## Questions?
Contact me on IRC via c0d3z3r0 @ freenode.net

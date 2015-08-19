# rpi2strap for Raspberry Pi 2

## What is it?
rpi2strap is a script for installing Debian GNU/Linux Jessie 8.0 armhf to a sd card. You will get real Debian, not Raspbian!

## Why?
Why not? :-) I *hate* downloading big sd card images and dd'ing them onto my sd cards resulting in an overblown Raspbian installation with software I am never going to use. You'll simply get a basic Debian installation like from the netinstaller with some more basic packages (see below). Additionally you get armv7 compiled software instead of armv6 (raspbian). You can use more recent software and get Debian security updates much faster.

## What you will need and how to I use it
There is some software you have to install before using my installer:

* python3
* python3-colorama
* sed
* psmisc
* fdisk
* curl
* dosfstools
* cdebootstrap
* qemu-user-static.

If there is no package python3-colorama you can also install it with `pip3 install colorama` after installing `python3-pip` via aptitude / apt-get.

*You'll be warned if something is missing.*

## Usage
Just look at the help: ./rpi2strap.py -h

## Packages already included
- debian standard packages
- keyboard-configuration, console-data, console-setup
- ntp, tzdata, locales, openssh-server, ca-certificates, openssl
- cpufrequtils, cpufreqd, rpi-update, raspi-config, fake-hwclock
- vim, aptitude, apt-transport-https, psmisc

## I need some Raspbian packages like raspi-config!
No problem! The raspberrypi.org repository is included in the sources.list. If you need packages from there like gpio you have to select them manually in aptitude. They will *never* be installed by dependecy because we **don't want to mix them up** with Debian packages. We just want to use the repo for some specific packages. Btw. raspi-config and rpi-update are already included.

## I want wheezy instead of jessie
Open the script with vim and type `:%s/jessie/wheezy`. Then close vim with `:wq`. That's it.

## Warnings
rpi2strap is only working for Raspberry Pi 2. All prior versions like B or B+ are **NOT SUPPORTED!** This is because pi2 is armv7 while earlier boards have armv6 which isn't supported by Debian armhf.

When using the overclocking switch `-o` check that the config.txt (look inside my script) fits your needs. Graphics memory is set to the smallest possible value because I only use it as a server. Change it to your needs.

The installer enables SSH root login and password authentication so you can easily ssh to your new Debian installation. For security reasons you shouldn't use that in a production environment. Switch to pubkey authentication instead.

There have been error reports that this script doesn't work on Ubuntu so you need to use a Debian host.

## Am I allowed to modify and share it?
Yes, of course but please keep the author name where it is :-)

## Problems?
Open an issue on GitHub, please.

## Questions?
Contact me on IRC via c0d3z3r0 @ freenode.net

# License

Copyright (C) 2015 Michael Niewöhner

This is open source software, licensed under GPLv2. See the file LICENSE for details.

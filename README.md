# rpi2strap for Raspberry Pi 2

## What is it?
rpi2strap is a script for installing Debian GNU/Linux Jessie 8.0 armhf to a sd card. You will get real Debian, not Raspbian!

## Why?
Why not? :-) I *hate* downloading big sd card images and dd'ing them onto my sd cards resulting in an overblown Raspbian installation with software I would never use. You'll simply get a basic Debian installation like from the netinstaller. Additionally you can use more recent software and get Debian security updates faster.

## What you will need and how to I use it
There is some software you have to install: grep, curl, csplit, dosfstools and cdebootstrap. You need an ethernet connection. **The installer does not work with wifi!**

./rpi2strap /dev/[your sdcard]
Follow the instructions. After this first stage plug in ethernet, HDMI and a keyboard and power up your Raspberry Pi 2. The installation will continue and after a reboot you can login with root:toor.

## I need some Raspbian packages like raspi-config!
Yeah, me too. At this time you need to install the packages by hand or compile them from source. Later I'm going to include the Raspbian repository and install the most important packages by default. First I have to figure out how this APT pinning thingy really works so that we **don't mix up Raspbian and Debian** packages. We just want to use the repo for some specific packages.

## Warnings
rpi2strap is only working for Raspberry Pi 2. Every prior versions like B or B+ are **NOT SUPPORTED!** This is because pi2 is armv7 while earlier boards have armv6 which isn't supported by Debian armhf.

Please check that the config.txt (look inside my script) fits your needs. It has HDMI/DVI and overclocking enabled. Graphics memory is set to the smallest possible value because I only use it as a server.

The installer enables SSH root login and password authentication so you can easily ssh to your new Debian installation. For security reasons you shouldn't use that in an production environment. Switch to pubkey authentication instead.

## TODO
- Figure out how apt pinning works and add Raspbian repo

## Am I allowed to modify and share it?
Yes, of course but please keep the author name where it is :-)

## Questions?
Contact me on IRC via c0d3z3r0 @ freenode.net
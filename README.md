# rpi2strap for Raspberry Pi 2

## What is it?
rpi2strap is a script for installing Debian GNU/Linux Jessie 8.0 armhf to a sd card. You will get real Debian, not raspbian!

## Why?
Just because I *hate* downloading big sd card images a dd'ing them onto my sd cards. Additionally you can use more recent software and get debian security updates faster.

## Is it ready to use?
No. It will work more or less but it is not complete, yet. I will make some changes in the next days.


## What you will need and how to I use it
There is some software you have to install: grep, curl, csplit, dosfstools and cdebootstrap.

./rpi2strap /dev/[your sdcard]

## I need some raspbian packages like raspi-config!
Yeah, me too. At this time you need to install them by hand. Later I'm going to include the raspbian repository and install the most important packages by default. First I have to figure out how this APT pinning thingy really works so that we don't mix up raspbian and debian packages. We just want to use the repo for some specific packages.

## Warnings
Please check that the config.txt (look inside my script) fits your needs. It has HDMI/DVI and overclocking enabled. Graphics memory is set to the smallest possible value because I only use it as a server.

## TODO
- Figure out how apt pinning works and add raspbian repo
- Test the installer


## Am I allowed to modify and share it?
Yes, of course but please keep the author name where it is :-)

## Questions?
Contact me on IRC via c0d3z3r0 @ freenode.net
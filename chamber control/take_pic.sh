#!/bin/bash

name=$2
camera1=$1

v4l2-ctl --set-ctrl brightness=80
v4l2-ctl --set-ctrl saturation=70
v4l2-ctl --set-ctrl contrast=70

fswebcam --device $camera1 --resolution 1920x1080 --jpeg 85 --save $name

#!/bin/bash

name=$3
camera1=$1
res=$2

#echo name
#echo camera1
#echo res1


v4l2-ctl --set-ctrl brightness=80
v4l2-ctl --set-ctrl saturation=70
v4l2-ctl --set-ctrl contrast=70

fswebcam --device "$camera1" --resolution "$res" --jpeg 85 --save "$name"

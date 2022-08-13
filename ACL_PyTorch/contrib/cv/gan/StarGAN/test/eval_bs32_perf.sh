#!/bin/bash

source ./test/env_npu.sh

./msame --model "./StarGAN_bs32.om"  --input "./bin/img",'./bin/attr' --output "./output_bs32" --outfmt TXT > StarGAN_bs32.log

DIR="output_bs32"
mkdir $DIR

if [ "$(ls -A $DIR)" ]; then
  echo "Turn to txt success!"
  echo "Begin to infer!"
else
  echo "Turn to txt fail!"
  exit -1
fi

perf_str=`grep "Inference average time : " StarGAN_bs32.log`
if [ -n "$perf_str" ]; then
    perf_num=`echo $perf_str | awk -F ' ' '{print $5}'`
    echo "(310 bs32) Inference average time:" $perf_num "ms"
else
  echo "fail!"
  exit -1
fi

awk 'BEGIN{printf "(310 bs32) FPS:%.3f\n", 1000*1/('$perf_num'/128)}'
# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2017
# All rights reserved.
# Copyright 2022 Huawei Technologies Co., Ltd
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================

# Copyright (c) OpenMMLab. All rights reserved.
import argparse
import json

import mmcv

from mmocr.utils import list_to_file


def parse_coco_json(in_path):
    json_obj = mmcv.load(in_path)
    image_infos = json_obj['images']
    annotations = json_obj['annotations']
    imgid2imgname = {}
    img_ids = []
    for image_info in image_infos:
        imgid2imgname[image_info['id']] = image_info
        img_ids.append(image_info['id'])
    imgid2anno = {}
    for img_id in img_ids:
        imgid2anno[img_id] = []
    for anno in annotations:
        img_id = anno['image_id']
        new_anno = {}
        new_anno['iscrowd'] = anno['iscrowd']
        new_anno['category_id'] = anno['category_id']
        new_anno['bbox'] = anno['bbox']
        new_anno['segmentation'] = anno['segmentation']
        if img_id in imgid2anno.keys():
            imgid2anno[img_id].append(new_anno)

    return imgid2imgname, imgid2anno


def gen_line_dict_file(out_path, imgid2imgname, imgid2anno):
    lines = []
    for key, value in imgid2imgname.items():
        if key in imgid2anno:
            anno = imgid2anno[key]
            line_dict = {}
            line_dict['file_name'] = value['file_name']
            line_dict['height'] = value['height']
            line_dict['width'] = value['width']
            line_dict['annotations'] = anno
            lines.append(json.dumps(line_dict))
    list_to_file(out_path, lines)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in-path', help='input json path with coco format')
    parser.add_argument(
        '--out-path', help='output txt path with line-json format')

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    imgid2imgname, imgid2anno = parse_coco_json(args.in_path)
    gen_line_dict_file(args.out_path, imgid2imgname, imgid2anno)
    print('finish')


if __name__ == '__main__':
    main()
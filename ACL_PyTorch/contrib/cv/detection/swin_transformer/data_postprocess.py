# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import torch
import argparse
import cv2
import numpy as np
import copy

def postprocess_bboxes(bboxes, image_size, net_input_width, net_input_height):
    w = image_size[0]
    h = image_size[1]
    scale = min(net_input_width / w, net_input_height / h)

    pad_w = net_input_width - w * scale
    pad_h = net_input_height - h * scale
    pad_left = pad_w // 2
    pad_top = pad_h // 2

    bboxes[:, 0] = (bboxes[:, 0] - pad_left) / scale
    bboxes[:, 1] = (bboxes[:, 1] - pad_top)  / scale
    bboxes[:, 2] = (bboxes[:, 2] - pad_left) / scale
    bboxes[:, 3] = (bboxes[:, 3] - pad_top)  / scale

    # bboxes[:, :4] *= (bboxes[:, :4] > 0).astype(bboxes.dtype)

    return bboxes

def postprocess_masks(masks, image_size, net_input_width, net_input_height):
    w = image_size[0]
    h = image_size[1]
    scale = min(net_input_width / w, net_input_height / h)

    pad_w = net_input_width - w * scale
    pad_h = net_input_height - h * scale
    pad_left = pad_w // 2
    pad_top = pad_h // 2

    if pad_top < 0:
        pad_top = 0
    if pad_left < 0:
        pad_left = 0
    top = int(pad_top)
    left = int(pad_left)
    hs = int(pad_top + net_input_height - pad_h)
    ws = int(pad_left + net_input_width - pad_w)
    masks = masks.to(dtype=torch.float32)
    res_append = torch.zeros(0, h, w)
    if torch.cuda.is_available():
        res_append = res_append.to(device='cuda')
    for i in range(masks.size(0)):
        mask = masks[i][top:hs, left:ws]
        mask = mask.expand((1, 1, mask.size(0), mask.size(1)))
        mask = F.interpolate(mask, size=(int(h), int(w)), mode='bilinear', align_corners=False)
        mask = mask[0][0]
        mask = mask.unsqueeze(0)
        res_append = torch.cat((res_append, mask))

    return res_append[:, None]

import pickle
def save_variable(v, filename):
    f = open(filename, 'wb')
    pickle.dump(v, f)
    f.close()
def load_variavle(filename):
    f = open(filename, 'rb')
    r = pickle.load(f)
    f.close()
    return r

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_annotation", default="./origin_pictures.info")
    parser.add_argument("--bin_data_path", default="./result/dumpOutput_device0/")
    parser.add_argument("--det_results_path", default="./detection-results/")
    parser.add_argument("--anno_path", default="data/coco/annotations/instances_val2017.json")
    parser.add_argument("--data_path", default="data/coco/images/")
    parser.add_argument("--net_out_num", type=int, default=3)
    parser.add_argument("--net_input_width", type=int, default=1216)
    parser.add_argument("--net_input_height", type=int, default=800)
    parser.add_argument("--ifShowDetObj", action="store_true", help="if input the para means True, neither False.")
    flags = parser.parse_args()
    flags.bin_data_path = os.path.join(flags.bin_data_path, sorted(os.listdir(flags.bin_data_path))[-1])

    img_size_dict = dict()
    with open(flags.test_annotation)as f:
        for line in f.readlines():
            temp = line.split(" ")
            img_file_path = temp[1]
            img_name = temp[1].split("/")[-1].split(".")[0]
            img_width = int(temp[2])
            img_height = int(temp[3])
            img_size_dict[img_name] = (img_width, img_height, img_file_path)

    bin_path = flags.bin_data_path
    det_results_path = flags.det_results_path
    os.makedirs(det_results_path, exist_ok=True)
    #total_img = set([name[:name.rfind('_')] for name in os.listdir(bin_path) if "bin" in name])

    import glob
    import torch
    from torchvision.models.detection.roi_heads import paste_masks_in_image
    from mmdet.models.roi_heads.mask_heads.fcn_mask_head import _do_paste_mask
    import torch.nn.functional as F
    from mmdet.core import bbox2result
    from mmdet.core import encode_mask_results
    from mmdet.datasets import CocoDataset
    from mmdet.datasets import build_dataloader, build_dataset
    from torchvision.ops import nms
    # coco_dataset = CocoDataset(ann_file='./data/coco/annotations/instances_val2017.json', pipeline=[])
    coco_dataset = build_dataset({'type': 'CocoDataset', 'ann_file': flags.anno_path,
                             'img_prefix': flags.data_path, 'pipeline': [{'type': 'LoadImageFromFile'},
                                                                              {'type': 'MultiScaleFlipAug',
                                                                               'img_scale': (1333, 800), 'flip': False,
                                                                               'transforms': [{'type': 'Resize',
                                                                                               'keep_ratio': True},
                                                                                              {'type': 'RandomFlip'},
                                                                                              {'type': 'Normalize',
                                                                                               'mean': [123.675, 116.28,
                                                                                                        103.53],
                                                                                               'std': [58.395, 57.12,
                                                                                                       57.375],
                                                                                               'to_rgb': True},
                                                                                              {'type': 'Pad',
                                                                                               'size_divisor': 32},
                                                                                              {'type': 'ImageToTensor',
                                                                                               'keys': ['img']},
                                                                                              {'type': 'Collect',
                                                                                               'keys': ['img']}]}],
                             'test_mode': True})

    coco_class_map = {id:name for id, name in enumerate(coco_dataset.CLASSES)}
    #print(dir(coco_dataset))
    results = []

    cnt = 0
    #for bin_file in sorted(total_img):
    infer_failed = []
    needtopop = []
    data_infos = copy.copy(coco_dataset.data_infos)
    for idx, data in enumerate(data_infos):
        ids = data['id']
        result = []
        cnt = cnt + 1
        bin_file_l = glob.glob(bin_path + '/*0' + str(ids) + '_output_1.bin')
        if len(bin_file_l) > 0:
            bin_file = bin_file_l[0]
            bin_file = bin_file[bin_file.rfind('/') + 1:]
            bin_file = bin_file[:bin_file.rfind('_')]
            print(cnt - 1, bin_file)
            path_base = os.path.join(bin_path, bin_file)
            bin_name = bin_file.split('_')[0]
            res_buff = []
            bbox_results = []
            cls_segms = []

            for num in range(1, flags.net_out_num + 1):
                if num == 1:
                    buf = np.fromfile(path_base + "_" + str(num - 1) + ".bin", dtype="float32")
                    buf = np.reshape(buf, [100, 5])
                elif num == 2:
                    try:
                        buf = np.fromfile(path_base + "_" + str(num - 1) + ".bin", dtype="int32")
                        buf = np.reshape(buf, [100, 1])
                    except:
                        buf = np.fromfile(path_base + "_" + str(num - 1) + ".bin", dtype="int64")
                        buf = np.reshape(buf, [100, 1])
                elif num == 3:
                    bboxes = np.fromfile(path_base + "_" + str(num - 3) + ".bin", dtype="float32")
                    bboxes = np.reshape(bboxes, [100, 5])
                    bboxes = torch.from_numpy(bboxes)
                    try:
                        labels = np.fromfile(path_base + "_" + str(num - 2) + ".bin", dtype="int32")
                        labels = np.reshape(labels, [100, 1])
                    except:
                        labels = np.fromfile(path_base + "_" + str(num - 2) + ".bin", dtype="int64")
                        labels = np.reshape(labels, [100, 1])
                    labels = torch.from_numpy(labels)

                    mask_pred = np.fromfile(path_base + "_" + str(num - 1) + ".bin", dtype="float32")
                    mask_pred = np.reshape(mask_pred, [100, 80, 28, 28])
                    mask_pred = torch.from_numpy(mask_pred)

                    keep = bboxes[:, 4] > 0.05
                    # # keepidx = nms(bboxes[keep,:4], bboxes[keep,4:], 0.5)
                    bboxes = bboxes[keep].reshape(-1, 5)
                    labels = labels[keep].reshape(-1, 1)
                    mask_pred = mask_pred[keep].reshape(-1, 80, 28, 28)

                    if torch.cuda.is_available():
                        mask_pred = mask_pred.to(device='cuda')

                    img_shape = (flags.net_input_height, flags.net_input_width)
                    mask_pred = mask_pred[range(len(mask_pred)), labels[:, 0].numpy()][:, None]
                    masks, _ = _do_paste_mask(mask_pred, bboxes[:, :4], flags.net_input_height, flags.net_input_width, skip_empty=False)
                    masks = masks >= 0.5
                    masks = postprocess_masks(masks, img_size_dict[bin_name], flags.net_input_width, flags.net_input_height)
                    if torch.cuda.is_available():
                        masks = masks.cpu()

                    cls_segms = [[] for _ in range(80)]
                    for i in range(len(masks)):
                        cls_segms[labels[i][0]].append(masks[i][0].numpy())

                    bboxes = postprocess_bboxes(bboxes.numpy(), img_size_dict[bin_name], flags.net_input_width, flags.net_input_height)
                    bbox_results = [bbox2result(torch.from_numpy(bboxes), labels[:, 0], 80)]
                res_buff.append(buf)

            result = list(zip(bbox_results, [cls_segms]))
            result = [(bbox_results, encode_mask_results(mask_results)) for bbox_results, mask_results in result]
            results.extend(result)
            current_img_size = img_size_dict[bin_name]
            res_bboxes = np.concatenate(res_buff, axis=1)
            predbox = res_bboxes[keep].reshape(-1,7)
            predbox = postprocess_bboxes(res_bboxes, current_img_size, flags.net_input_width, flags.net_input_height)

            if flags.ifShowDetObj == True:
                imgCur = cv2.imread(current_img_size[2])

            det_results_str = ''
            for idx, class_idx in enumerate(predbox[:, 5]):
                if float(predbox[idx][4]) < float(0.3):
                    continue
                if class_idx < 0 or class_idx > 80:
                    continue

                class_name = coco_class_map[int(class_idx)]
                det_results_str += "{} {} {} {} {} {}\n".format(class_name, str(predbox[idx][4]), predbox[idx][0],
                                                                predbox[idx][1], predbox[idx][2], predbox[idx][3])
                if flags.ifShowDetObj == True:
                    imgCur = cv2.rectangle(imgCur, (int(predbox[idx][0]), int(predbox[idx][1])), (int(predbox[idx][2]), int(predbox[idx][3])), (0,255,0), 2)
                    imgCur = cv2.putText(imgCur, class_name, (int(predbox[idx][0]), int(predbox[idx][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            if flags.ifShowDetObj == True:
                cv2.imwrite(os.path.join(det_results_path, bin_name +'.jpg'), imgCur, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

            det_results_file = os.path.join(det_results_path, bin_name + ".txt")
            with open(det_results_file, "w") as detf:
                detf.write(det_results_str)
        else:
            print("[ERROR] file not exist", path_base + "_1.bin")
            needtopop.append(idx)
    print(needtopop)
    for idx in sorted(needtopop)[::-1]:
        coco_dataset.data_infos.pop(idx)
        coco_dataset.img_ids.pop(idx)
    save_variable(results, './results.txt')
    # results = load_variavle('./results.txt')

    eval_results = coco_dataset.evaluate(results, metric=['bbox', 'segm'], classwise=True)
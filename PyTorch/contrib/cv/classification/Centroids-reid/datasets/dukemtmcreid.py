# encoding: utf-8
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
"""
Partially based on work by:
@author:  liaoxingyu
@contact: liaoxingyu2@jd.com

Adapted and extended by:
@author: mikwieczorek
"""

import glob
import os.path as osp
import re
from collections import defaultdict

import pytorch_lightning as pl
from torch.utils.data import (DataLoader, Dataset, DistributedSampler,
                              SequentialSampler)

from .bases import (BaseDatasetLabelled, BaseDatasetLabelledPerPid,
                    ReidBaseDataModule, collate_fn_alternative, pil_loader)
from .samplers import get_sampler
from .transforms import ReidTransforms


class DukeMTMCreID(ReidBaseDataModule):
    """
    DukeMTMC-reID
    Reference:
    1. Ristani et al. Performance Measures and a Data Set for Multi-Target, Multi-Camera Tracking. ECCVW 2016.
    2. Zheng et al. Unlabeled Samples Generated by GAN Improve the Person Re-identification Baseline in vitro. ICCV 2017.
    URL: https://github.com/layumi/DukeMTMC-reID_evaluation

    Dataset statistics:
    # identities: 1404 (train + query)
    # images:16522 (train) + 2228 (query) + 17661 (gallery)
    # cameras: 8

     Version that will not supply resampled instances
    """
    dataset_dir = 'DukeMTMC-reID'
    def __init__(self, cfg, **kwargs):
        super().__init__(cfg, **kwargs)
        self.dataset_dir = cfg.DATASETS.ROOT_DIR
        self.train_dir = osp.join(self.dataset_dir, 'DukeMTMC-reID/bounding_box_train')
        self.query_dir = osp.join(self.dataset_dir, 'DukeMTMC-reID/query')
        self.gallery_dir = osp.join(self.dataset_dir, 'DukeMTMC-reID/bounding_box_test')

    def setup(self):
        self._check_before_run()
        transforms_base = ReidTransforms(self.cfg)

        train, train_dict = self._process_dir(self.train_dir, relabel=True)
        self.train_dict = train_dict
        self.train_list = train
        query, query_dict = self._process_dir(self.query_dir, relabel=False)
        gallery, gallery_dict  = self._process_dir(self.gallery_dir, relabel=False)
        self.query_list = query
        self.gallery_list = gallery

        self.train = BaseDatasetLabelledPerPid(train_dict, transforms_base.build_transforms(is_train=True), self.num_instances, self.cfg.DATALOADER.USE_RESAMPLING)
        self.val = BaseDatasetLabelled(query+gallery, transforms_base.build_transforms(is_train=False))

        self._print_dataset_statistics(train, query, gallery)
        # For reid_metic to evaluate properly
        num_query_pids, num_query_imgs, num_query_cams = self._get_imagedata_info(query)
        num_train_pids, num_train_imgs, num_train_cams = self._get_imagedata_info(train)
        self.num_query = len(query)
        self.num_classes = num_train_pids

    def _process_dir(self, dir_path, relabel=False):
        img_paths = glob.glob(osp.join(dir_path, '*.jpg'))
        pattern = re.compile(r'([-\d]+)_c(\d)')

        pid_container = set()
        for img_path in img_paths:
            pid, _ = map(int, pattern.search(img_path).groups())
            pid_container.add(pid)
        pid2label = {pid: label for label, pid in enumerate(pid_container)}

        dataset_dict = defaultdict(list)
        dataset = []
        for idx, img_path in enumerate(img_paths):
            pid, camid = map(int, pattern.search(img_path).groups())
            assert 1 <= camid <= 8
            camid -= 1  # index starts from 0
            if relabel: pid = pid2label[pid]
            dataset.append((img_path, pid, camid, idx))
            dataset_dict[pid].append((img_path, pid, camid, idx))

        return dataset, dataset_dict

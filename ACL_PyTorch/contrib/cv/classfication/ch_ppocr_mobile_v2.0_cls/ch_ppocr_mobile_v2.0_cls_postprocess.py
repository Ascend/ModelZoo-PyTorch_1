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
import sys

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__)
sys.path.append(os.path.abspath(os.path.join(__dir__, 'PaddleOCR')))

import paddle
import numpy as np
import tools.program as program

from tqdm import tqdm
from ppocr.postprocess import build_post_process


def main(config, device, logger, vdl_writer):
    global_config = config['Global']
    
    post_process_class = build_post_process(config['PostProcess'], global_config)
    
    pbar = tqdm(
            total=5,
            desc='Postprocessing',
            position=0,
            leave=True)
        
    post_results = {}
    for idx in range(1, 6):
        result_name = 'word_{}_0.bin'.format(idx)
        result = os.path.join(config['results'], result_name)
        
        pred = paddle.to_tensor(np.fromfile(result, dtype=np.float32).reshape(1, 2))
        
        post_result = post_process_class(pred)
        
        im_name = 'word_{}.jpg'.format(idx)
        post_results[im_name] = post_result
        
        pbar.update(1)
    
    pbar.close()
    print("Infer Results: ", post_results)


if __name__ == '__main__':
    config, device, logger, vdl_writer = program.preprocess()
    main(config, device, logger, vdl_writer)
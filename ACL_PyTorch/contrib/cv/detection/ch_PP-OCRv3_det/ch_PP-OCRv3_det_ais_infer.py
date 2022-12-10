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
import shutil
import argparse
from tqdm import tqdm
from pathlib import Path

import numpy as np


def ais_infer(ais_infer, model, input_dir, output_dir):

    output_dir = Path(output_dir)
    if output_dir.is_dir():
        shutil.rmtree(str(output_dir))
    output_dir.mkdir(parents=True)
    tmp_dir = Path('inference_temp_dir')
    tmp_dir.mkdir(parents=True, exist_ok=True)
    data_paths = [path for path in Path(input_dir).iterdir()]

    for data_path in tqdm(data_paths):
        data_npy = np.load(data_path)
        n, c, h, w = data_npy.shape
        
        infer_cmd = f'python3 {ais_infer} --model={model} --input={str(data_path)} \
                    --output={tmp_dir} --output_dirname=out --dymHW={h},{w} --outfmt=NPY'

        print(infer_cmd)
        state = os.system(infer_cmd)
        assert state == 0, f"bash cmd exect failed: {infer_cmd}"

        stem = data_path.stem
        shutil.move(str(tmp_dir/'out'/f'{stem}_0.npy'), str(output_dir))
        print(f"Infer Results Saved To: {str(output_dir)}")
        shutil.rmtree(str(tmp_dir/'out'))



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='ais infer')
    parser.add_argument('--ais_infer', default='./ais_infer/ais_infer.py', 
                        type=str, help='path to ais_infer.py')
    parser.add_argument('--model', type=str, help='om model path')
    parser.add_argument('--input', type=str, help='input directory path')
    parser.add_argument('--output', type=str, help='output directory path')    
    args = parser.parse_args()

    ais_infer(args.ais_infer, args.model, args.input, args.output)

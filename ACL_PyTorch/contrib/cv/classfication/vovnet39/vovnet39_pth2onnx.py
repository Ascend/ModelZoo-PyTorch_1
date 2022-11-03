# Copyright 2021 Huawei Technologies Co., Ltd
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

import torch
import sys
sys.path.append(r"./cnn_train/VoVNet.pytorch")
import models_vovnet

def pth2onnx(input_file, output_file):
    model = models_vovnet.vovnet39(pretrained=False)
    device_ids = [0]
    model = torch.nn.DataParallel(model, device_ids=device_ids)
    checkpoint = torch.load(input_file, map_location='cpu')
    model.load_state_dict(checkpoint)
    model = model.module
    model.eval()
    input_names = ["image"]
    output_names = ["class"]
    dynamic_axes = {'image': {0: '-1'}, 'class': {0: '-1'}}
    dummy_input = torch.rand(1, 3, 224, 224)
    torch.onnx.export(model, dummy_input, output_file,
                      input_names=input_names,
                      dynamic_axes=dynamic_axes,
                      output_names=output_names,
                      opset_version=11,
                      verbose=False)


if __name__ == "__main__":
    pth2onnx(sys.argv[1], sys.argv[2])

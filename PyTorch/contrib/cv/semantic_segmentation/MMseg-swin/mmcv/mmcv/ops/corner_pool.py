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
import torch
from torch import Tensor, nn
from torch.autograd import Function

_mode_dict = {'top': 0, 'bottom': 1, 'left': 2, 'right': 3}


def _corner_pool(x: Tensor, dim: int, flip: bool) -> Tensor:
    size = x.size(dim)
    output = x.clone()

    ind = 1
    while ind < size:
        if flip:
            cur_start = 0
            cur_len = size - ind
            next_start = ind
            next_len = size - ind
        else:
            cur_start = ind
            cur_len = size - ind
            next_start = 0
            next_len = size - ind

        # max_temp should be cloned for backward computation
        max_temp = output.narrow(dim, cur_start, cur_len).clone()
        cur_temp = output.narrow(dim, cur_start, cur_len)
        next_temp = output.narrow(dim, next_start, next_len)

        cur_temp[...] = torch.where(max_temp > next_temp, max_temp, next_temp)

        ind = ind << 1

    return output


class TopPoolFunction(Function):

    @staticmethod
    def symbolic(g, input: Tensor) -> Tensor:
        output = g.op(
            'mmcv::MMCVCornerPool', input, mode_i=int(_mode_dict['top']))
        return output

    @staticmethod
    def forward(ctx, input: Tensor) -> Tensor:
        return _corner_pool(input, 2, True)


class BottomPoolFunction(Function):

    @staticmethod
    def symbolic(g, input: Tensor) -> Tensor:
        output = g.op(
            'mmcv::MMCVCornerPool', input, mode_i=int(_mode_dict['bottom']))
        return output

    @staticmethod
    def forward(ctx, input: Tensor) -> Tensor:
        return _corner_pool(input, 2, False)


class LeftPoolFunction(Function):

    @staticmethod
    def symbolic(g, input: Tensor) -> Tensor:
        output = g.op(
            'mmcv::MMCVCornerPool', input, mode_i=int(_mode_dict['left']))
        return output

    @staticmethod
    def forward(ctx, input: Tensor) -> Tensor:
        return _corner_pool(input, 3, True)


class RightPoolFunction(Function):

    @staticmethod
    def symbolic(g, input: Tensor) -> Tensor:
        output = g.op(
            'mmcv::MMCVCornerPool', input, mode_i=int(_mode_dict['right']))
        return output

    @staticmethod
    def forward(ctx, input: Tensor) -> Tensor:
        return _corner_pool(input, 3, False)


class CornerPool(nn.Module):
    """Corner Pooling.

    Corner Pooling is a new type of pooling layer that helps a
    convolutional network better localize corners of bounding boxes.

    Please refer to `CornerNet: Detecting Objects as Paired Keypoints
    <https://arxiv.org/abs/1808.01244>`_ for more details.

    Code is modified from https://github.com/princeton-vl/CornerNet-Lite.

    Args:
        mode (str): Pooling orientation for the pooling layer

            - 'bottom': Bottom Pooling
            - 'left': Left Pooling
            - 'right': Right Pooling
            - 'top': Top Pooling

    Returns:
        Feature map after pooling.
    """

    pool_functions = {
        'bottom': BottomPoolFunction,
        'left': LeftPoolFunction,
        'right': RightPoolFunction,
        'top': TopPoolFunction,
    }

    cummax_dim_flip = {
        'bottom': (2, False),
        'left': (3, True),
        'right': (3, False),
        'top': (2, True),
    }

    def __init__(self, mode: str):
        super().__init__()
        assert mode in self.pool_functions
        self.mode = mode
        self.corner_pool: Function = self.pool_functions[mode]

    def forward(self, x: Tensor) -> Tensor:
        if torch.__version__ != 'parrots' and torch.__version__ >= '1.5.0':
            if torch.onnx.is_in_onnx_export():
                assert torch.__version__ >= '1.7.0', \
                    'When `cummax` serves as an intermediate component whose '\
                    'outputs is used as inputs for another modules, it\'s '\
                    'expected that pytorch version must be >= 1.7.0, '\
                    'otherwise Error appears like: `RuntimeError: tuple '\
                    'appears in op that does not forward tuples, unsupported '\
                    'kind: prim::PythonOp`.'

            dim, flip = self.cummax_dim_flip[self.mode]
            if flip:
                x = x.flip(dim)
            pool_tensor, _ = torch.cummax(x, dim=dim)
            if flip:
                pool_tensor = pool_tensor.flip(dim)
            return pool_tensor
        else:
            if torch.onnx.is_in_onnx_export():
                return self.corner_pool.apply(x)
            else:
                dim, flip = self.cummax_dim_flip[self.mode]
                return _corner_pool(x, dim, flip)

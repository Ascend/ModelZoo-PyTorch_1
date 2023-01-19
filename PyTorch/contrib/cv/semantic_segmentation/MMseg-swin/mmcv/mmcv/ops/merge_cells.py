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
import math
from abc import abstractmethod
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from ..cnn import ConvModule


class BaseMergeCell(nn.Module):
    """The basic class for cells used in NAS-FPN and NAS-FCOS.

    BaseMergeCell takes 2 inputs. After applying convolution
    on them, they are resized to the target size. Then,
    they go through binary_op, which depends on the type of cell.
    If with_out_conv is True, the result of output will go through
    another convolution layer.

    Args:
        fused_channels (int): number of input channels in out_conv layer.
        out_channels (int): number of output channels in out_conv layer.
        with_out_conv (bool): Whether to use out_conv layer
        out_conv_cfg (dict): Config dict for convolution layer, which should
            contain "groups", "kernel_size", "padding", "bias" to build
            out_conv layer.
        out_norm_cfg (dict): Config dict for normalization layer in out_conv.
        out_conv_order (tuple): The order of conv/norm/activation layers in
            out_conv.
        with_input1_conv (bool): Whether to use convolution on input1.
        with_input2_conv (bool): Whether to use convolution on input2.
        input_conv_cfg (dict): Config dict for building input1_conv layer and
            input2_conv layer, which is expected to contain the type of
            convolution.
            Default: None, which means using conv2d.
        input_norm_cfg (dict): Config dict for normalization layer in
            input1_conv and input2_conv layer. Default: None.
        upsample_mode (str): Interpolation method used to resize the output
            of input1_conv and input2_conv to target size. Currently, we
            support ['nearest', 'bilinear']. Default: 'nearest'.
    """

    def __init__(self,
                 fused_channels: Optional[int] = 256,
                 out_channels: Optional[int] = 256,
                 with_out_conv: bool = True,
                 out_conv_cfg: dict = dict(
                     groups=1, kernel_size=3, padding=1, bias=True),
                 out_norm_cfg: Optional[dict] = None,
                 out_conv_order: tuple = ('act', 'conv', 'norm'),
                 with_input1_conv: bool = False,
                 with_input2_conv: bool = False,
                 input_conv_cfg: Optional[dict] = None,
                 input_norm_cfg: Optional[dict] = None,
                 upsample_mode: str = 'nearest'):
        super().__init__()
        assert upsample_mode in ['nearest', 'bilinear']
        self.with_out_conv = with_out_conv
        self.with_input1_conv = with_input1_conv
        self.with_input2_conv = with_input2_conv
        self.upsample_mode = upsample_mode

        if self.with_out_conv:
            self.out_conv = ConvModule(
                fused_channels,  # type: ignore
                out_channels,  # type: ignore
                **out_conv_cfg,
                norm_cfg=out_norm_cfg,
                order=out_conv_order)

        self.input1_conv = self._build_input_conv(
            out_channels, input_conv_cfg,
            input_norm_cfg) if with_input1_conv else nn.Sequential()
        self.input2_conv = self._build_input_conv(
            out_channels, input_conv_cfg,
            input_norm_cfg) if with_input2_conv else nn.Sequential()

    def _build_input_conv(self, channel, conv_cfg, norm_cfg):
        return ConvModule(
            channel,
            channel,
            3,
            padding=1,
            conv_cfg=conv_cfg,
            norm_cfg=norm_cfg,
            bias=True)

    @abstractmethod
    def _binary_op(self, x1, x2):
        pass

    def _resize(self, x, size):
        if x.shape[-2:] == size:
            return x
        elif x.shape[-2:] < size:
            return F.interpolate(x, size=size, mode=self.upsample_mode)
        else:
            if x.shape[-2] % size[-2] != 0 or x.shape[-1] % size[-1] != 0:
                h, w = x.shape[-2:]
                target_h, target_w = size
                pad_h = math.ceil(h / target_h) * target_h - h
                pad_w = math.ceil(w / target_w) * target_w - w
                pad_l = pad_w // 2
                pad_r = pad_w - pad_l
                pad_t = pad_h // 2
                pad_b = pad_h - pad_t
                pad = (pad_l, pad_r, pad_t, pad_b)
                x = F.pad(x, pad, mode='constant', value=0.0)
            kernel_size = (x.shape[-2] // size[-2], x.shape[-1] // size[-1])
            x = F.max_pool2d(x, kernel_size=kernel_size, stride=kernel_size)
            return x

    def forward(self,
                x1: torch.Tensor,
                x2: torch.Tensor,
                out_size: Optional[tuple] = None) -> torch.Tensor:
        assert x1.shape[:2] == x2.shape[:2]
        assert out_size is None or len(out_size) == 2
        if out_size is None:  # resize to larger one
            out_size = max(x1.size()[2:], x2.size()[2:])

        x1 = self.input1_conv(x1)
        x2 = self.input2_conv(x2)

        x1 = self._resize(x1, out_size)
        x2 = self._resize(x2, out_size)

        x = self._binary_op(x1, x2)
        if self.with_out_conv:
            x = self.out_conv(x)
        return x


class SumCell(BaseMergeCell):

    def __init__(self, in_channels: int, out_channels: int, **kwargs):
        super().__init__(in_channels, out_channels, **kwargs)

    def _binary_op(self, x1, x2):
        return x1 + x2


class ConcatCell(BaseMergeCell):

    def __init__(self, in_channels: int, out_channels: int, **kwargs):
        super().__init__(in_channels * 2, out_channels, **kwargs)

    def _binary_op(self, x1, x2):
        ret = torch.cat([x1, x2], dim=1)
        return ret


class GlobalPoolingCell(BaseMergeCell):

    def __init__(self,
                 in_channels: Optional[int] = None,
                 out_channels: Optional[int] = None,
                 **kwargs):
        super().__init__(in_channels, out_channels, **kwargs)
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))

    def _binary_op(self, x1, x2):
        x2_att = self.global_pool(x2).sigmoid()
        return x2 + x2_att * x1

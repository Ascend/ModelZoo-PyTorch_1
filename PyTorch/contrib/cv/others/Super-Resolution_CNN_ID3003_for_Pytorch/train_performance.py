#!/usr/bin/env python
# coding=utf-8

# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
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
# ============================================================================
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
# ============================================================================

"""
Author  : Xu fuyong
Time    : created by 2019/7/16 20:17

"""

import argparse
import os
import copy

import torch
import torch.npu
if torch.__version__>= '1.8.1':
      import torch_npu
from torch import nn
import torch.optim as optim
import torch.backends.cudnn as cudnn
from torch.utils.data.dataloader import DataLoader
from tqdm import tqdm

import apex
from apex import amp

from model import SRCNN
from datasets import TrainDataset, EvalDataset
from utils import AverageMeter, calc_psnr

import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument('--train-file', type=str,default='processed_data/T91_Y_channel/T91_x3.h5', required=True)
    # parser.add_argument('--eval-file', type=str, default='processed_data/Set5_Y_channel/Set_x3.h5',required=True)
    parser.add_argument('--data_url',type=str,
                        default='/home/ma-user/modelarts/inputs/data_url_0/',
                        # required=True
                        )
    parser.add_argument('--train_url', type=str,
                        default='/home/ma-user/modelarts/outputs/train_url_0/',
                        # required=True
                        )
    # parser.add_argument('--train-file', type=str,
    #                     # default='processed_data/T91_Y_channel/T91_x3.h5',
    #                     default='T91_x3.h5',
    #                     required=False)
    # parser.add_argument('--eval-file', type=str,
    #                     # default='processed_data/Set5_Y_channel/Set_x3.h5',
    #                     default='Set5_x3.h5',
    #                     required=False)
    parser.add_argument('--outputs-dir', type=str, default='output',required=False)
    parser.add_argument('--scale', type=int, default=3)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--num-workers', type=int, default=8)
    parser.add_argument('--num-epochs', type=int, default=500)
    parser.add_argument('--seed', type=int, default=123)
    args = parser.parse_args()

    args.outputs_dir = os.path.join(args.outputs_dir, 'x{}'.format(args.scale))

    if not os.path.exists(args.outputs_dir):
        os.makedirs(args.outputs_dir)

    cudnn.benchmark = True
    # device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    device = torch.npu.set_device('npu:0')

    torch.manual_seed(args.seed)

    # model = SRCNN().to(device)
    model = SRCNN().npu()
    criterion = nn.MSELoss().npu()
    # optimizer = optim.Adam([
    #     {'params': model.conv1.parameters()},
    #     {'params': model.conv2.parameters()},
    #     {'params': model.conv3.parameters(), 'lr': args.lr*0.1}
    # ], lr=args.lr)
    # optimizer = apex.optimizers.NpuFusedSGD(model.parameters(), lr=args.lr, momentum=0.9)
    # optimizer = apex.optimizers.NpuFusedSGD([
    #     {'params': model.conv1.parameters()},
    #     {'params': model.conv2.parameters()},
    #     {'params': model.conv3.parameters(), 'lr': args.lr*0.1}
    # ],lr=args.lr)
    optimizer = apex.optimizers.NpuFusedAdam([
        {'params': model.conv1.parameters()},
        {'params': model.conv2.parameters()},
        {'params': model.conv3.parameters(), 'lr': args.lr*0.1}
    ],lr=args.lr)

    # optimizer = apex.optimizers.NpuFusedAdam(model.parameters(),lr=args.lr)
    model, optimizer = amp.initialize(model,optimizer,opt_level='O2',loss_scale=32.0,combine_grad=True)
    # amp.register_half_function(torch, 'bmm')  # bmm会强制使用half进行计算
    # amp.register_float_function(torch, 'bmm')  # bmm会强制使用float进行计算

    # train_dataset = TrainDataset(args.train_file)
    # train_dataset = TrainDataset(args.data_url)
    train_dataset = TrainDataset(os.path.join(args.data_url,'train','T91_x3.h5'))
    # train_dataset = TrainDataset('processed_data/T91_Y_channel/T91_x3.h5')
    train_dataloader = DataLoader(dataset=train_dataset,
                                  batch_size=args.batch_size,
                                  shuffle=True,
                                  num_workers=args.num_workers,
                                  pin_memory=True,
                                  drop_last=True)

    # eval_dataset = EvalDataset(args.eval_file)
    eval_dataset = EvalDataset(os.path.join(args.data_url,'val','Set5_x3.h5'))
    # eval_dataset = EvalDataset('processed_data/Set5_Y_channel/Set_x3.h5')
    eval_dataloader = DataLoader(dataset=eval_dataset, batch_size=1)

    best_weights = copy.deepcopy(model.state_dict())
    best_epoch = 0
    best_psnr = 0.0

    for epoch in range(args.num_epochs):
        model.train()
        epoch_losses = AverageMeter()
        batch_time = AverageMeter()

#         with tqdm(total=(len(train_dataset) - len(train_dataset) % args.batch_size)) as t:
#         with tqdm(total=(len(train_dataset) - len(train_dataset) % args.batch_size),ncols=100) as t:
#             t.set_description('epoch:{}/{}'.format(epoch, args.num_epochs - 1))

        i = 0
        runtime = 0
        train_loss = 0.0

        for data in train_dataloader:
            start = time.time()
            inputs, labels = data

            # inputs = inputs.to(device)
            # labels = labels.to(device)

            inputs = inputs.npu()
            labels = labels.npu()

            # with torch.autograd.profiler.profile(use_npu=True) as prof:
            #     preds = model(inputs)
            #     loss = criterion(preds, labels)
            #     optimizer.zero_grad()
            #     # if amp_mode:
            #     with amp.scale_loss(loss, optimizer) as scaled_loss:
            #         scaled_loss.backward()
            #     # else:
            #     #     loss.backward()
            #     optimizer.step()
            # print(prof.key_averages().table(sort_by="self_cpu_time_total"))
            # prof.export_chrome_trace("output.prof")  # "output.prof"为输出文件地址

            preds = model(inputs)
            preds = preds.npu_format_cast(2)
            loss = criterion(preds, labels)

            # epoch_losses.update(loss.item(), len(inputs))

            optimizer.zero_grad()
            # loss.backward()
            with amp.scale_loss(loss, optimizer) as scaled_loss:
                scaled_loss.backward()
            optimizer.step()
            train_loss += loss.item()
            runtime += (time.time() - start)
            i+=1

#                 t.set_postfix(loss='{:.6f}'.format(epoch_losses.avg))
#                 t.set_postfix(loss='{:.6f}'.format(epoch_losses.avg),each_step_time='{:.6f}'.format(runtime/i))
                # t.update(len(inputs))
        print('epoch{}'.format(epoch) + ' : ' + 'loss={:.6f}, each_step_time={:.6f}'.format(train_loss/i, runtime/i))
        torch.save(model.state_dict(), os.path.join(args.outputs_dir, 'epoch_{}.pth'.format(epoch)))
        # torch.save(model.state_dict(), os.path.join('output', 'epoch_{}.pth'.format(epoch)))

        model.eval()
        epoch_psnr = AverageMeter()

        for data in eval_dataloader:
            inputs, labels = data

            # inputs = inputs.to(device)
            # labels = labels.to(device)

            inputs = inputs.npu()
            labels = labels.npu()

            with torch.no_grad():
                preds = model(inputs).clamp(0.0, 1.0)

            epoch_psnr.update(calc_psnr(preds, labels), len(inputs))

        print('eval psnr: {:.2f}'.format(epoch_psnr.avg))

        if epoch_psnr.avg > best_psnr:
            best_epoch = epoch
            best_psnr = epoch_psnr.avg
            best_weights = copy.deepcopy(model.state_dict())

    print('best epoch: {}, psnr: {:.2f}'.format(best_epoch, best_psnr))
    torch.save(best_weights, os.path.join(args.outputs_dir, 'best.pth'))
    # torch.save(best_weights, os.path.join('output', 'best.pth'))
# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import math
import os
import random
import shutil
import sys
import time
import warnings

import torch
import numpy as np
import apex
from apex import amp
import torch.nn as nn
import torch.nn.parallel
import torch.npu
import torch.backends.cudnn as cudnn
import torch.distributed as dist
import torch.optim
import torch.multiprocessing as mp
import torch.utils.data
import torch.utils.data.distributed
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import models.resnet_0_6_0 as resnet_0_6_0
import moxing as mox
from collections import OrderedDict

CACHE_DATA_URL = '/cache/data_url'
CACHE_TRAIN_URL = '/cache/train_url'

parser = argparse.ArgumentParser(description='PyTorch ImageNet Training')
parser.add_argument('--data_url', metavar='DIR',required=True,
                    help='path to dataset')
parser.add_argument('--train_url', metavar='DIR',required=True,
                    help='path to output')
parser.add_argument('--train_dir', default='train', type=str, help='train dir')
parser.add_argument('--val_dir', default='val', type=str, help='val dir')

parser.add_argument('-j', '--workers', default=4, type=int, metavar='N',
                    help='number of data loading workers (default: 4)')
parser.add_argument('--epochs', default=90, type=int, metavar='N',
                    help='number of total epochs to run')
parser.add_argument('--start-epoch', default=0, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('-b', '--batch-size', default=256, type=int,
                    metavar='N',
                    help='mini-batch size (default: 256), this is the total '
                         'batch size of all GPUs on the current node when '
                         'using Data Parallel or Distributed Data Parallel')
parser.add_argument('--lr', '--learning-rate', default=0.1, type=float,
                    metavar='LR', help='initial learning rate', dest='lr')
parser.add_argument('--momentum', default=0.9, type=float, metavar='M',
                    help='momentum')
parser.add_argument('--wd', '--weight-decay', default=1e-4, type=float,
                    metavar='W', help='weight decay (default: 1e-4)',
                    dest='weight_decay')
parser.add_argument('-p', '--print-freq', default=10, type=int,
                    metavar='N', help='print frequency (default: 10)')
parser.add_argument('--resume', default='', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')
parser.add_argument('-e', '--evaluate', dest='evaluate', action='store_true',
                    help='evaluate model on validation set')
parser.add_argument('--seed', default=49, type=int,
                    help='seed for initializing training. ')
parser.add_argument('--gpu', default=0, type=int,
                    help='GPU id to use.')
parser.add_argument('--pretrained', dest='pretrained', action='store_true',
                    help='use pre-trained model')
parser.add_argument('--world-size', default=-1, type=int,
                    help='number of nodes for distributed training')
parser.add_argument('--rank', default=-1, type=int,
                    help='node rank for distributed training')
parser.add_argument('--dist-url', default='tcp://224.66.41.62:23456', type=str,
                    help='url used to set up distributed training')
parser.add_argument('--dist-backend', default='nccl', type=str,
                    help='distributed backend')
parser.add_argument('--multiprocessing-distributed', action='store_true',
                    help='Use multi-processing distributed training to launch '
                         'N processes per node, which has N GPUs. This is the '
                         'fastest way to use PyTorch for either single node or '
                         'multi node data parallel training')
parser.add_argument('--addr', default='10.136.181.115', type=str, help='master addr')
parser.add_argument('--device-list', default='0,1,2,3,4,5,6,7', type=str, help='device id list')
parser.add_argument('--device', default='npu', type=str, help='npu or gpu')
parser.add_argument('--warm_up_epochs', default=0, type=int,
                    help='warm up')
parser.add_argument('--amp', default=False, action='store_true',
                    help='use amp to train the model')
parser.add_argument('--opt-level', default='O2', type=str, help='apex optimize level')
parser.add_argument('--loss-scale-value', default='1024', type=int, help='static loss scale value')

parser.add_argument('--stop-step-num', default=None, type=int, help='after the stop-step, killing the training task')
parser.add_argument('--eval-freq', default=10, type=int, help='test interval')


best_acc1 = 0
cur_step = 0

def device_id_to_process_device_map(device_list):
    devices = device_list.split(",")
    devices = [int(x) for x in devices]
    devices.sort()

    process_device_map = dict()
    for process_id, device_id in enumerate(devices):
        process_device_map[process_id] = device_id

    return process_device_map

def seed_everything(seed, device):
    random.seed(seed)
    torch.manual_seed(seed)
    cudnn.deterministic = True

def main():
    args = parser.parse_args()
    if not os.path.exists(CACHE_DATA_URL):
        os.makedirs(CACHE_DATA_URL)
    if not os.path.exists(CACHE_TRAIN_URL):
        os.makedirs(CACHE_TRAIN_URL)

    mox.file.copy_parallel(args.data_url, CACHE_DATA_URL)
    print("===============main()=================")
    print(args)
    print("===============main()=================")

    os.environ['KERNEL_NAME_ID'] = str(0)
    print("++++++++++++++++++ KERNEL_NAME_ID:", os.environ['KERNEL_NAME_ID'])

    os.environ['MASTER_ADDR'] = args.addr
    os.environ['MASTER_PORT'] = '59629'

    if args.dist_url == "env://" and args.world_size == -1:
        args.world_size = int(os.environ["WORLD_SIZE"])

    args.distributed = args.world_size > 1 or args.multiprocessing_distributed

    args.process_device_map = device_id_to_process_device_map(args.device_list)

    if 'npu' in args.device:
        import torch.npu

    if args.seed is not None:
        seed_everything(args.seed, args.device)
        warnings.warn('You have chosen to seed training. '
                      'This will turn on the CUDNN deterministic setting, '
                      'which can slow down your training considerably! '
                      'You may see unexpected behavior when restarting '
                      'from checkpoints.')



    ngpus_per_node = len(args.process_device_map)
    print("============main :", args.gpu)

    if args.multiprocessing_distributed:
        args.world_size = ngpus_per_node * args.world_size
        if args.device == 'npu':
            print("device = npu")
            mp.spawn(main_worker, nprocs=ngpus_per_node, args=(ngpus_per_node, args))
        else:
            print("device != npu")
            mp.spawn(main_worker, nprocs=ngpus_per_node, args=(ngpus_per_node, args))
    else:
        main_worker(args.gpu, ngpus_per_node, args)

def main_worker(gpu, ngpus_per_node, args):
    global best_acc1
    print("============main worker:", gpu)

    args.gpu = args.process_device_map[gpu]
    print("============main worker:", args.gpu)

    print("[npu id:", args.gpu, "]", "++++++++++++++++ before set KERNEL_NAME_ID:", os.environ['KERNEL_NAME_ID'])
    os.environ['KERNEL_NAME_ID'] = str(gpu)
    print("[npu id:", args.gpu, "]", "++++++++++++++++ KERNEL_NAME_ID:", os.environ['KERNEL_NAME_ID'])

    if args.gpu is not None:
        print("[npu id:", args.gpu, "]", "Use GPU: {} for training".format(args.gpu))

    if args.distributed:
        if args.dist_url == "env://" and args.rank == -1:
            args.rank = int(os.environ["RANK"])
        if args.multiprocessing_distributed:
            # For multiprocessing distributed training, rank needs to be the
            # global rank among all the processes
            args.rank = args.rank * ngpus_per_node + gpu

        if args.device == 'npu':
            dist.init_process_group(backend=args.dist_backend,  # init_method=args.dist_url,
                                    world_size=args.world_size, rank=args.rank)
        else:
            dist.init_process_group(backend=args.dist_backend, init_method=args.dist_url,
                                    world_size=args.world_size, rank=args.rank)

    if args.device == 'npu':
        loc = 'npu:{}'.format(args.gpu)
        torch.npu.set_device(loc)
    else:
        loc = 'cuda:{}'.format(args.gpu)
        torch.cuda.set_device(loc)

    args.batch_size = int(args.batch_size / ngpus_per_node)
    args.workers = int((args.workers + ngpus_per_node - 1) / ngpus_per_node)

    print("[npu id:", args.gpu, "]", "===============main_worker()=================")
    print("[npu id:", args.gpu, "]", args)
    print("[npu id:", args.gpu, "]", "===============main_worker()=================")

    if args.pretrained:
        print("=> using pre-trained model wide_resnet50_2")
        model = resnet_0_6_0.wide_resnet50_2(num_classes=args.num_classes)
        print("loading model of yours...")
        pretrained_dict = torch.load("./model_best.pth.tar", map_location="cpu")["state_dict"]
        if "fc.weight" in pretrained_dict:
            pretrained_dict.pop('fc.weight')
            pretrained_dict.pop('fc.bias')
        model.load_state_dict(pretrained_dict, strict=False)
    else:
        print("=> creating model wide_resnet50_2")
        model = resnet_0_6_0.wide_resnet50_2()

    model = model.to(loc)

    # define loss function (criterion) and optimizer
    optimizer = apex.optimizers.NpuFusedSGD(model.parameters(), args.lr,
                                            momentum=args.momentum,
                                            weight_decay=args.weight_decay)

    criterion = nn.CrossEntropyLoss().to(loc)

    if args.amp:
        model, optimizer = amp.initialize(model, optimizer, opt_level=args.opt_level, loss_scale=args.loss_scale_value)
    if args.distributed:
        model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[args.gpu], broadcast_buffers=False)

    # optionally resume from a checkpoint
    if args.resume:
        if os.path.isfile(args.resume):
            print("=> loading checkpoint '{}'".format(args.resume))
            checkpoint = torch.load(args.resume, map_location=loc)
            args.start_epoch = checkpoint['epoch']
            best_acc1 = checkpoint['best_acc1']
            model.load_state_dict(checkpoint['state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer'])
            if args.amp:
                amp.load_state_dict(checkpoint['amp'])
            print("=> loaded checkpoint '{}' (epoch {})"
                  .format(args.resume, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(args.resume))

    # Data loading code
    #traindir = os.path.join(CACHE_DATA_URL)
    traindir = os.path.join(CACHE_DATA_URL, args.train_dir)
    valdir = os.path.join(CACHE_DATA_URL, args.val_dir)

    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])

    train_dataset = datasets.ImageFolder(
        traindir,
        transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ]))
    val_dataset = datasets.ImageFolder(valdir, transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                normalize,
            ]))

    if args.distributed:
        train_sampler = torch.utils.data.distributed.DistributedSampler(train_dataset)
        val_sampler = torch.utils.data.distributed.DistributedSampler(val_dataset)
    else:
        train_sampler = None
        val_sampler = None

    train_loader = torch.utils.data.DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=(
                train_sampler is None),
        num_workers=args.workers, pin_memory=False, sampler=train_sampler, drop_last=True)

    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=args.batch_size, shuffle=True,
        num_workers=args.workers, pin_memory=False, drop_last=True)

    if args.evaluate:
        validate(val_loader, model, criterion, args, ngpus_per_node)
        return

    for epoch in range(args.start_epoch, args.epochs):
        if args.distributed:
            train_sampler.set_epoch(epoch)
        adjust_learning_rate(optimizer, epoch, args)
        # train for one epoch
        train(train_loader, model, criterion, optimizer, epoch, args, ngpus_per_node)

        if (epoch + 1) % args.eval_freq == 0 or epoch == args.epochs - 1:
            # evaluate on validation set
            acc1 = validate(val_loader, model, criterion, args, ngpus_per_node)

            # remember best acc@1 and save checkpoint
            is_best = acc1 > best_acc1
            best_acc1 = max(acc1, best_acc1)

            # save checkpoint
            if not args.multiprocessing_distributed or \
                    (args.multiprocessing_distributed and args.rank % ngpus_per_node == 0):
                if args.amp:
                    save_checkpoint({
                        'epoch': epoch + 1,
                        'state_dict': model.state_dict(),
                        'best_acc1': best_acc1,
                        'optimizer': optimizer.state_dict(),
                        'amp': amp.state_dict(),
                    }, is_best)

                else:
                    save_checkpoint({
                        'epoch': epoch + 1,
                        'state_dict': model.state_dict(),
                        'best_acc1': best_acc1,
                        'optimizer': optimizer.state_dict(),
                    }, is_best)

        if args.stop_step_num is not None and cur_step >= args.stop_step_num:
            break
    convert()
    mox.file.copy_parallel(CACHE_TRAIN_URL, args.train_url)


def train(train_loader, model, criterion, optimizer, epoch, args, ngpus_per_node):
    batch_time = AverageMeter('Time', ':6.3f', start_count_index=5)
    data_time = AverageMeter('Data', ':6.3f', start_count_index=5)
    losses = AverageMeter('Loss', ':6.8f')
    top1 = AverageMeter('Acc@1', ':6.2f')
    top5 = AverageMeter('Acc@5', ':6.2f')
    progress = ProgressMeter(
        len(train_loader),
        [batch_time, data_time, losses, top1, top5],
        prefix="Epoch: [{}]".format(epoch))

    # switch to train mode
    model.train()

    if 'npu' in args.device:
        loc = 'npu:{}'.format(args.gpu)
    else:
        loc = 'cuda:{}'.format(args.gpu)

    end = time.time()
    steps_per_epoch = len(train_loader)
    for i, (images, target) in enumerate(train_loader):
        # measure data loading time
        data_time.update(time.time() - end)

        if 'npu' in args.device:
            target = target.to(torch.int32)

        if 'npu' in args.device or 'cuda' in args.device:
            images = images.to(loc, non_blocking=True)
            target = target.to(loc, non_blocking=True)

        if 'npu' in args.device:
            stream = torch.npu.current_stream()
        else:
            stream = torch.cuda.current_stream()

        # compute output
        output = model(images)
        stream.synchronize()

        loss = criterion(output, target)
        stream.synchronize()

        # measure accuracy and record loss
        acc1, acc5 = accuracy(output, target, topk=(1, 5))
        losses.update(loss.item(), images.size(0))
        top1.update(acc1[0], images.size(0))
        top5.update(acc5[0], images.size(0))

        # compute gradient and do SGD step
        optimizer.zero_grad()
        stream.synchronize()
        if args.amp:
            with amp.scale_loss(loss, optimizer) as scaled_loss:
                scaled_loss.backward()
        else:
            loss.backward()
        stream.synchronize()
        optimizer.step()
        stream.synchronize()

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0:
            if not args.multiprocessing_distributed or (args.multiprocessing_distributed
                                                        and args.rank % ngpus_per_node == 0):
                progress.display(i)
            if i > 400:
                pass

    if not args.multiprocessing_distributed or (args.multiprocessing_distributed
                                                and args.rank % ngpus_per_node == 0):
        print("[npu id:", args.gpu, "]", '* FPS@all {:.3f}'.format(ngpus_per_node * args.batch_size / batch_time.avg))


def validate(val_loader, model, criterion, args, ngpus_per_node):
    batch_time = AverageMeter('Time', ':6.3f')
    losses = AverageMeter('Loss', ':.4e')
    top1 = AverageMeter('Acc@1', ':6.2f')
    top5 = AverageMeter('Acc@5', ':6.2f')
    progress = ProgressMeter(
        len(val_loader),
        [batch_time, losses, top1, top5],
        prefix='Test: ')

    # switch to evaluate mode
    model.eval()

    if 'npu' in args.device:
        loc = 'npu:{}'.format(args.gpu)
    else:
        loc = 'cuda:{}'.format(args.gpu)

    with torch.no_grad():
        end = time.time()
        for i, (images, target) in enumerate(val_loader):

            if 'npu' in args.device:
                target = target.to(torch.int32)

            if 'npu' in args.device or 'cuda' in args.device:
                images = images.to(loc, non_blocking=True)
                target = target.to(loc, non_blocking=True)

            # compute output
            output = model(images)
            loss = criterion(output, target)

            # measure accuracy and record loss
            acc1, acc5 = accuracy(output, target, topk=(1, 5))
            losses.update(loss.item(), images.size(0))
            top1.update(acc1[0], images.size(0))
            top5.update(acc5[0], images.size(0))

            # measure elapsed time
            batch_time.update(time.time() - end)
            end = time.time()

            if i % args.print_freq == 0:
                if not args.multiprocessing_distributed or \
                        (args.multiprocessing_distributed and args.rank % ngpus_per_node == 0):
                    progress.display(i)

        if not args.multiprocessing_distributed or \
                (args.multiprocessing_distributed and args.rank % ngpus_per_node == 0):
            print("[npu id:", args.gpu, "]", '[AVG-ACC] * Acc@1 {top1.avg:.3f} Acc@5 {top5.avg:.3f}'
                  .format(top1=top1, top5=top5))

    return top1.avg


def save_checkpoint(state, is_best, filename='checkpoint.pth.tar'):
    # torch.save(state, os.path.join(CACHE_TRAIN_URL, 'checkpoint.pth.tar'))
    file_path = os.path.join(CACHE_TRAIN_URL, 'checkpoint.pth.tar')
    torch.save(state, filename)
    torch.save(state, file_path)
    if is_best:
        shutil.copyfile(filename, 'model_best.pth.tar')


'''export'''


def proc_node_module(checkpoint, AttrName):
    new_state_dict = OrderedDict()
    for k, v in checkpoint[AttrName].items():
        if(k[0:7] == "module."):
            name = k[7:]
        else:
            name = k[0:]
        new_state_dict[name] = v
    return new_state_dict


def convert():
    args = parser.parse_args()
    loc = 'cpu'
    checkpoint = torch.load("./checkpoint.pth.tar", map_location=loc)
    print("loadckpt success")
    checkpoint['state_dict'] = proc_node_module(checkpoint, 'state_dict')
    model = resnet_0_6_0.wide_resnet50_2().to(loc)
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    print(model)

    input_names = ["actual_input_1"]
    output_names = ["output1"]
    dummy_input = torch.randn(1, 3, 224, 224).to(loc)
    path_onnx = os.path.join(CACHE_TRAIN_URL, "wide_resnet50.onnx")
    torch.onnx.export(model, dummy_input, path_onnx, input_names=input_names, output_names=output_names,
                      opset_version=11)


'''export end'''


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self, name, fmt=':f', start_count_index=0):
        self.name = name
        self.fmt = fmt
        self.reset()
        self.start_count_index = start_count_index

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        if self.count == 0:
            self.N = n

        self.val = val
        self.count += n

        if self.count > (self.start_count_index * self.N):
            self.sum += val * n
            self.avg = self.sum / (self.count - self.start_count_index * self.N)

    def __str__(self):
        fmtstr = '{name} {val' + self.fmt + '} ({avg' + self.fmt + '})'
        return fmtstr.format(**self.__dict__)


class ProgressMeter(object):
    def __init__(self, num_batches, meters, prefix=""):
        self.batch_fmtstr = self._get_batch_fmtstr(num_batches)
        self.meters = meters
        self.prefix = prefix

    def display(self, batch):
        entries = [self.prefix + self.batch_fmtstr.format(batch)]
        entries += [str(meter) for meter in self.meters]
        print('\t'.join(entries))

    def _get_batch_fmtstr(self, num_batches):
        num_digits = len(str(num_batches // 1))
        fmt = '{:' + str(num_digits) + 'd}'
        return '[' + fmt + '/' + fmt.format(num_batches) + ']'


def adjust_learning_rate(optimizer, epoch, args):
    """warm up cosine annealing learning rate."""

    if args.warm_up_epochs > 0 and epoch < args.warm_up_epochs:
        lr = args.lr * ((epoch + 1) / (args.warm_up_epochs + 1))
    else:
        alpha = 0
        cosine_decay = 0.5 * (
                1 + np.cos(np.pi * (epoch - args.warm_up_epochs) / (args.epochs - args.warm_up_epochs)))
        decayed = (1 - alpha) * cosine_decay + alpha
        lr = args.lr * decayed

    print("=> Epoch[%d] Setting lr: %.4f" % (epoch, lr))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr


def accuracy(output, target, topk=(1,)):
    """Computes the accuracy over the k top predictions for the specified values of k"""
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size))
        return res


if __name__ == '__main__':
    main()

# /bin/bash run_train.sh 'obs://mindx-user-4/WideResNet50_2_ID1627_for_PyTorch/code/' 'code/pthtar2onnx.py' '/tmp/log/training.log' --data_url 'obs://mindx-user-4/WideResNet50_2_ID1627_for_PyTorch/pretrained/pth/' --train_url 'obs://mindx-user-4/WideResNet50_2_ID1627_for_PyTorch/pretrained/onnx/' --seed=49 --workers=128 --learning-rate=0.1 --mom=0.9 --world-size=1 --weight-decay=0.0005 --print-freq=1 --device='npu' --gpu=0 --dist-backend 'hccl' --epochs=1 --warm_up_epochs=5  --loss-scale=32 --amp --batch-size=256



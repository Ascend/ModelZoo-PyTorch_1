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

# Copyright (c) 2019-2021 NVIDIA CORPORATION. All rights reserved.
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

import sys
import subprocess
import os
import socket
from argparse import ArgumentParser, REMAINDER

import torch


def parse_args():
    """
    Helper function parsing the command line options
    @retval ArgumentParser
    """
    parser = ArgumentParser(description="PyTorch distributed training launch "
                                        "helper utilty that will spawn up "
                                        "multiple distributed processes")

    # Optional arguments for the launch helper
    parser.add_argument("--nnodes", type=int, default=1,
                        help="The number of nodes to use for distributed "
                             "training")
    parser.add_argument("--node_rank", type=int, default=0,
                        help="The rank of the node for multi-node distributed "
                             "training")
    parser.add_argument("--nproc_per_node", type=int, default=8,
                        help="The number of processes to launch on each node, "
                             "for GPU training, this is recommended to be set "
                             "to the number of GPUs in your system so that "
                             "each process can be bound to a single GPU.")
    parser.add_argument("--master_addr", default="127.0.0.1", type=str,
                        help="Master node (rank 0)'s address, should be either "
                             "the IP address or the hostname of node 0, for "
                             "single node multi-proc training, the "
                             "--master_addr can simply be 127.0.0.1")
    parser.add_argument("--master_port", default=29688, type=int,
                        help="Master node (rank 0)'s free port that needs to "
                             "be used for communciation during distributed "
                             "training")
    parser.add_argument('--no_hyperthreads', action='store_true',
                        help='Flag to disable binding to hyperthreads')
    parser.add_argument('--no_membind', action='store_true',
                        help='Flag to disable memory binding')

    # non-optional arguments for binding
    parser.add_argument("--nsockets_per_node", type=int, required=True,
                        help="Number of CPU sockets on a node")
    parser.add_argument("--ncores_per_socket", type=int, required=True,
                        help="Number of CPU cores per socket")

    # positional
    parser.add_argument("training_script", type=str,
                        help="The full path to the single GPU training "
                             "program/script to be launched in parallel, "
                             "followed by all the arguments for the "
                             "training script")

    # rest from the training program
    parser.add_argument('training_script_args', nargs=REMAINDER)
    parser.add_argument("--data_path", type=str, default='')
    return parser.parse_args()


def main():
    args = parse_args()

    # variables for numactrl binding

    NSOCKETS = args.nsockets_per_node
    NGPUS_PER_SOCKET = (args.nproc_per_node // args.nsockets_per_node) + (
        1 if (args.nproc_per_node % args.nsockets_per_node) else 0)
    NCORES_PER_GPU = args.ncores_per_socket // NGPUS_PER_SOCKET

    # world size in terms of number of processes
    dist_world_size = args.nproc_per_node * args.nnodes

    # set PyTorch distributed related environmental variables
    current_env = os.environ.copy()
    current_env["MASTER_ADDR"] = args.master_addr
    current_env["MASTER_PORT"] = str(args.master_port)
    current_env["WORLD_SIZE"] = str(dist_world_size)
    current_env['NODE_RANK'] = str(args.node_rank)

    processes = []

    for local_rank in range(0, args.nproc_per_node):
        # each process's rank
        dist_rank = args.nproc_per_node * args.node_rank + local_rank
        current_env["RANK"] = str(dist_rank)
        current_env['LOCAL_RANK'] = str(local_rank)

        # form numactrl binding command
        cpu_ranges = [local_rank * NCORES_PER_GPU,
                      (local_rank + 1) * NCORES_PER_GPU - 1,
                      local_rank * NCORES_PER_GPU + (NCORES_PER_GPU * NGPUS_PER_SOCKET * NSOCKETS),
                      (local_rank + 1) * NCORES_PER_GPU + (NCORES_PER_GPU * NGPUS_PER_SOCKET * NSOCKETS) - 1]

        numactlargs = []
        if args.no_hyperthreads:
            numactlargs += ["--physcpubind={}-{}".format(*cpu_ranges[0:2])]
        else:
            numactlargs += ["--physcpubind={}-{},{}-{}".format(*cpu_ranges)]

        if not args.no_membind:
            memnode = local_rank // NGPUS_PER_SOCKET
            numactlargs += ["--membind={}".format(memnode)]

        # spawn the processes
        cmd = ["/usr/bin/numactl"] \
              + numactlargs \
              + [sys.executable,
                 "-u",
                 args.training_script,
                 "--local_rank={}".format(local_rank)
                 ] \
              + args.training_script_args

        process = subprocess.Popen(cmd, env=current_env)
        processes.append(process)

    for process in processes:
        process.wait()


if __name__ == "__main__":
    main()

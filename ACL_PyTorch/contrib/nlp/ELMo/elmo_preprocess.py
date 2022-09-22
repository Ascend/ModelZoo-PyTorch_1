import argparse
from allennlp.modules.elmo import batch_to_ids
import os
import numpy as np
import torch

def main():
        parser = argparse.ArgumentParser()
        parser.add_argument('--file_path', default='1-billion-word-language-modeling-benchmark-r13output/heldout-monolingual.tokenized.shuffled/',
                            help='path to dataset')
        parser.add_argument('--save_path', default='data.txt',
                            help='preprocess file')
        parser.add_argument('--bin_path', default='bin_path',
                            help='process file')
        parser.add_argument('--file_num', default=50, type=int,
                            help='test file number')
        parser.add_argument('--word_len', default=8, type=int,
                            help='words length')

        opt = parser.parse_args()
        save_file(opt)
        process_file(opt)

def read_news(fr):
    with open(fr, 'r',  encoding='utf-8') as f:
        lines = f.readlines()
        return [line for line in lines]

def save_file(opt):
        with open(opt.save_path, 'w', encoding='utf-8') as f:
                for i in range(opt.file_num):
                        if i < 10:
                                fr = '{}news.en.heldout-0000{}-of-00050'.format(opt.file_path, i)
                        else:
                                fr = '{}news.en.heldout-000{}-of-00050'.format(opt.file_path, i)
                        lines = read_news(fr)
                        for line in lines: # 读取每一行
                                if len(line.strip().split()) <= opt.word_len:
                                        f.write(line)

def read_file(opt):
    with open(opt.save_path, 'r',  encoding='utf-8') as f:
        contexts = []
        lines = f.readlines()
        for line in lines:
            context = line.strip().split(' ')
            contexts.append(context)
        return contexts

def process_file(opt):
        if not os.path.exists(opt.bin_path):
                os.makedirs(opt.bin_path)
        contexts = read_file(opt)
        pad = torch.randint(261, 262, (1, 1, 50))
        for i in range(len(contexts)):
                context = [contexts[i]]
                ids = batch_to_ids(context)
                if ids.shape[1] < opt.word_len:
                        gap = opt.word_len - ids.shape[1]
                        for _ in range(gap):
                                ids = torch.cat((ids, pad), 1)
                print(ids.shape)
                ids_np = np.asarray(ids, dtype=np.int32)
                bin_file_path = os.path.join(opt.bin_path, '{}.bin'.format(i))
                ids_np.tofile(bin_file_path)


if __name__ == '__main__':
        main()
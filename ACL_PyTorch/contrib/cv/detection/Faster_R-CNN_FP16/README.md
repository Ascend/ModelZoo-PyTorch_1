# Faster R-CNN-FP16模型-推理指导


- [概述](#ZH-CN_TOPIC_0000001172161501)

- [推理环境准备](#ZH-CN_TOPIC_0000001126281702)

- [快速上手](#ZH-CN_TOPIC_0000001126281700)

  - [获取源码](#section4622531142816)
  - [准备数据集](#section183221994411)
  - [模型推理](#section741711594517)

- [模型推理性能](#ZH-CN_TOPIC_0000001172201573)

- [配套环境](#ZH-CN_TOPIC_0000001126121892)

  ******

  

# 概述<a name="ZH-CN_TOPIC_0000001172161501"></a>

Faster-R-CNN 在Fast RCNN的基础上使用RPN层代替Selective Search提取候选框，同时引入anchor box，大幅提高了two-stage检测网络的速度，向实时检测迈进。


- 参考实现：

  ```
  url=https://github.com/open-mmlab/mmdetection/tree/master/configs/faster_rcnn
  branch=master
  commit_id=a21eb25535f31634cef332b09fc27d28956fb24b
  model_name=faster_rcnn_r50_fpn_fp16
  ```
  


  通过Git获取对应commit\_id的代码方法如下：

  ```
  git clone {repository_url}        # 克隆仓库的代码
  cd {repository_name}              # 切换到模型的代码仓目录
  git checkout {branch/tag}         # 切换到对应分支
  git reset --hard {commit_id}      # 代码设置到对应的commit_id（可选）
  cd {code_path}                    # 切换到模型代码所在路径，若仓库下只有该模型，则无需切换
  ```


## 输入输出数据<a name="section540883920406"></a>

- 输入数据

  | 输入数据 | 数据类型 | 大小                        | 数据排布格式 |
  | -------- | -------- | --------------------------- | ------------ |
  | input    | RGB_FP32 | batchsize x 3 x 1216 x 1216 | NCHW         |


- 输出数据

  | 输出数据 | 大小  | 数据类型 | 数据排布格式 |
  | -------- | ----- | -------- | ------------ |
  | boxes    | 100x5 | FLOAT32  | ND           |
  | labels   | 100   | INT64    | ND           |


# 推理环境准备\[所有版本\]<a name="ZH-CN_TOPIC_0000001126281702"></a>

- 该模型需要以下插件与驱动

  **表 1**  版本配套表

| 配套                                                         | 版本    | 环境准备指导                                                 |
| ------------------------------------------------------------ | ------- | ------------------------------------------------------------ |
| 固件与驱动                                                   | 1.0.15  | [Pytorch框架推理环境准备](https://www.hiascend.com/document/detail/zh/ModelZoo/pytorchframework/pies) |
| CANN                                                         | 5.1.RC1 | -                                                            |
| Python                                                       | 3.7.5   | -                                                            |
| PyTorch                                                      | 1.6.0   | -                                                            |
| 说明：Atlas 300I Duo 推理卡请以CANN版本选择实际固件与驱动版本。 | \       | \                                                            |

# 快速上手<a name="ZH-CN_TOPIC_0000001126281700"></a>

## 获取源码<a name="section4622531142816"></a>

1. 获取源码。

   ```
   git clone https://github.com/open-mmlab/mmdetection.git
   cd mmdetection
   git reset --hard a21eb25535f31634cef332b09fc27d28956fb24b
   pip3.7 install -v -e .
   ```

2. 修改mmdetection源码适配Ascend NPU。使用mmdetection（v2.8.0）导出onnx前, 
   需要对源码做一定的改动，以适配Ascend NPU。

   ```
   patch -p1 < ../mmdetection.patch
   cd ..
   ```

3. 安装依赖。

   ```
   conda install pytorch==1.7.0 torchvision==0.8.0 torchaudio==0.7.0 cudatoolkit=11.0 -c pytorch
   pip install mmcv-full==1.2.5 -f https://download.openmmlab.com/mmcv/dist/cu110/torch1.7.0/index.html
   pip3 install -r requirements.txt
   ```

## 准备数据集<a name="section183221994411"></a>

1. 获取原始数据集。（解压命令参考tar –xvf  \*.tar与 unzip \*.zip）

   该模型使用COCO官网的coco2017的5千张验证集进行测试，图片与标签分别存放在val2017/val2017/与annotations_trainval2017/annotations/instances_val2017.json。

   数据集链接：https://cocodataset.org/#download。

   数据预处理将原始数据集转换为模型输入的数据。

   将原始数据（.jpeg）转化为二进制文件（.bin）。转化方法参考mmdetection预处理方法，以获得最佳精度。以coco_2017数据集为例，通过缩放、均值方差手段归一化，输出为二进制文件。

   执行mmdetection_coco_preprocess.py脚本，完成预处理。

   ```
   python3.7 mmdetection_coco_preprocess.py --image_folder_path val2017/val2017/ --bin_folder_path val2017_bin
   ```

​	2.JPG图片info文件生成

后处理时需要输入数据集.jpg图片的info文件。使用get_info.py脚本，输入已经获得的图片文件,输出生成图片数据集的info文件。

运行get_info.py脚本。

```
	python3.7 get_info.py jpg ./val2017/val2017/ coco2017_jpg.info
```

第一个参数为生成的数据集文件格式，第二个参数为coco图片数据文件的**相对路径**，第三个参数为生成的数据集信息文件保存的路径。运行成功后，在当前目录中生成coco2017_jpg.info。

## 模型推理<a name="section741711594517"></a>

1. 模型转换。

   使用PyTorch将模型权重文件.pth转换为.onnx文件，再使用ATC工具将.onnx文件转为离线推理模型文件.om文件。

   1. 获取权重文件。

       [Faster-RCNN-R50-FPN-1X-COCO预训练pth权重文件](http://download.openmmlab.com/mmdetection/v2.0/faster_rcnn/faster_rcnn_r50_fpn_1x_coco/faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth)

   2. 修改cascade_rcnn_r50_fpn.py文件中nms_post参数

      打开文件。

      ```
      vi mmdetection/configs/_base_/models/cascade_rcnn_r50_fpn.py
      ```

      修改参数。

      ```
      test_cfg = dict(
          rpn=dict(
              nms_across_levels=False,
              nms_pre=1000,
              nms_post=500,
              max_num=1000,
              nms_thr=0.7,
              min_bbox_size=0),
          rcnn=dict(
              score_thr=0.05,
              nms=dict(type='nms', iou_threshold=0.5),
              max_per_img=100))
      ```

      说明：

      > 由于NPU RoiExtractor算子的特殊性，适当减少其输入框的数量可以在小幅度影响精度的基础上大幅度提高性能，推荐将test_cfg中rpn层的nms_post参数从1000改为500，用户可以自行决定是否应用此项改动。

   3. 导出onnx文件。

      使用mmdetection/tools目录中的pytorch2onnx导出onnx文件。运行pytorch2onnx脚本。

      ```
      python3.7 mmdetection/tools/pytorch2onnx.py mmdetection/configs/faster_rcnn/faster_rcnn_r50_fpn_1x_coco.py ./faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth --output-file faster_rcnn_r50_fpn.onnx --shape=1216 --verify --show
      ```

      获得faster_rcnn_r50_fpn.onnx文件。

   4. 使用ATC工具将ONNX模型转OM模型。

      1. 配置环境变量。

         ```
         source /usr/local/Ascend/ascend-toolkit/set_env.sh
         ```

         > **说明：** 
         >该脚本中环境变量仅供参考，请以实际安装环境配置环境变量。详细介绍请参见《[CANN 开发辅助工具指南 \(推理\)](https://support.huawei.com/enterprise/zh/ascend-computing/cann-pid-251168373?category=developer-documents&subcategory=auxiliary-development-tools)》。

      2. 执行命令查看芯片名称（$\{chip\_name\}）。

         ```
         npu-smi info
         #该设备芯片名为Ascend310P3 （自行替换）
         回显如下：
         +--------------------------------------------------------------------------------------------+
         | npu-smi 22.0.0                       Version: 22.0.2                                       |
         +-------------------+-----------------+------------------------------------------------------+
         | NPU     Name      | Health          | Power(W)     Temp(C)           Hugepages-Usage(page) |
         | Chip    Device    | Bus-Id          | AICore(%)    Memory-Usage(MB)                        |
         +===================+=================+======================================================+
         | 0       310P3     | OK              | 16.3         53                1236 / 1236           |
         | 0       0         | 0000:86:00.0    | 0            4060 / 21534                            |
         +===================+=================+======================================================+
         
         ```

      3. 执行ATC命令。
         ```
         atc --framework=5 --model=faster_rcnn_r50_fpn.onnx --output=faster_rcnn_r50_fpn --input_format=NCHW --input_shape="input:1,3,1216,1216" --log=debug --soc_version=Ascend${chip_name}
         ```

         - 参数说明：

           -   --model：为ONNX模型文件。
           -   --framework：5代表ONNX模型。
           -   --output：输出的OM模型。
           -   --input\_format：输入数据的格式。
           -   --input\_shape：输入数据的shape。
           -   --log：日志级别。
           -   --soc\_version：处理器型号。
           -   --insert\_op\_conf=aipp\_resnet34.config:  AIPP插入节点，通过config文件配置算子信息，功能包括图片色域转换、裁剪、归一化，主要用于处理原图输入数据，常与DVPP配合使用，详见下文数据预处理。

           运行成功后生成<u>***faster_rcnn_r50_fpn.om***</u>模型文件。

2. 开始推理验证。

   a.  使用ais-infer工具进行推理。

      ais-infer工具获取及使用方式请点击查看[[ais_infer 推理工具使用文档](https://gitee.com/ascend/tools/tree/master/ais-bench_workload/tool/ais_infer)]


   b.  执行推理。

```
python tools/ais-bench_workload/tool/ais_infer/ais_infer.py --model faster_rcnn_r50_fpn.om --input=val2017_bin --output=result
```
  -   参数说明：
       -   model：om文件路径。
       -   input：输入文件。
       -   output：输出文件所存目录。

  推理后的输出默认在当前目录result下。

  >**说明：** 
  >之后会在--output指定的文件夹result生成保存推理结果的文件夹，将其重命名为infer_result
  >执行ais-infer工具请选择与运行环境架构相同的命令。参数详情请参见。

   c.  精度验证。

 本模型提供后处理脚本，将二进制数据转化为txt文件，执行脚本。

```
python3.7 mmdetection_coco_postprocess.py --bin_data_path=result/infer_result --prob_thres=0.05 --det_results_path=detection-results --test_annotation=coco2017_jpg.info
```

- 参数说明：

   -   bin_data_path：推理输出目录。

   -   prob_thres：框的置信度阈值。

   -   det_results：后处理输出目录。

评测结果的mAP值需要使用官方的pycocotools工具，首先将后处理输出的txt文件转化为coco数据集评测精度的标准json格式。
执行转换脚本。

```
python3.7 txt_to_json.py
```
运行成功后，生成json文件。
调用coco_eval.py脚本，输出推理结果的详细评测报告。

```
python3.7 coco_eval.py --ground_truth=annotations_trainval2017/annotations/instances_val2017.json
```

> - ground_truth：instances_val2017.json所存放路径


# 模型推理性能&精度<a name="ZH-CN_TOPIC_0000001172201573"></a>

调用ACL接口推理计算，性能参考下列数据。

| 芯片型号 | Batch Size   | 数据集 | 精度 | 性能 |
| --------- | ---------------- | ---------- | ---------- | --------------- |
| Ascend310P | 1 | coco2017 | 37.2 | 15.759 |
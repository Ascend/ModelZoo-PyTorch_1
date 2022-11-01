# FLAVR模型-推理指导


- [概述](#ZH-CN_TOPIC_0000001172161501)
- [输入输出数据](#section540883920406)

- [推理环境准备](#ZH-CN_TOPIC_0000001126281702)

- [快速上手](#ZH-CN_TOPIC_0000001126281700)

  - [获取源码](#section4622531142816)
  - [准备数据集](#section183221994411)
  - [模型推理](#section741711594517)

- [模型推理性能&精度](#ZH-CN_TOPIC_0000001172201573)

  ******

  

# 概述<a name="ZH-CN_TOPIC_0000001172161501"></a>

FLAVR使用3D卷积来学习帧间运动信息，是一种无光流估计的单次预测视频插帧方法，可以进行一次多帧预测。


- 参考实现：

  ```
  url=https://github.com/tarun005/FLAVR
  commit_id=d23f17cd722a21d33957d506acb5c891c61a1db5
  code_path=bulit_in/cv/FLAVR_for_Pytorch
  model_name=FLAVR_4x
  ```
  



## 输入输出数据<a name="section540883920406"></a>

- 输入数据

  | 输入数据 | 数据类型 | 大小                      | 数据排布格式 |
  | -------- | -------- | ------------------------- | ------------ |
  | input_0  | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |
  | input_1  | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |
  | input_2  | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |
  | input_3  | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |


- 输出数据

  | 输出数据 | 数据类型 | 大小                      | 数据排布格式 |
  | -------- | -------- | ------------------------- | ------------ |
  | output_0 | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |
  | output_1 | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |
  | output_2 | RGB_FP32 | batchsize x 3 x 224 x 224 | NCHW         |



# 推理环境准备<a name="ZH-CN_TOPIC_0000001126281702"></a>

- 该模型需要以下插件与驱动

  **表 1**  版本配套表

  | 配套                                                         | 版本    | 环境准备指导                                                 |
  | ------------------------------------------------------------ | ------- | ------------------------------------------------------------ |
  | 固件与驱动                                                   | 22.0.3  | [Pytorch框架推理环境准备](https://www.hiascend.com/document/detail/zh/ModelZoo/pytorchframework/pies) |
  | CANN                                                         | 6.1.RC1 | -                                                            |
  | Python                                                       | 3.7.5   | -                                                            |
  | PyTorch                                                      | 1.12.1  | -                                                            |
  | 说明：Atlas 300I Duo 推理卡请以CANN版本选择实际固件与驱动版本。 | \       | \                                                            |



# 快速上手<a name="ZH-CN_TOPIC_0000001126281700"></a>

## 获取源码<a name="section4622531142816"></a>

1. 获取源码。

   ```
   git clone {repository_url}        # 克隆仓库的代码
   cd {repository_name}              # 切换到模型的代码仓目录
   git checkout {branch/tag}         # 切换到对应分支
   git reset --hard {commit_id}      # 代码设置到对应的commit_id（可选）
   cd {code_path}                    # 切换到模型代码所在路径，若仓库下只有该模型，则无需切换
   ```
2. 获取本仓源码，和上述第一步的源码文件夹放在同级目录下。

3. 安装依赖。

   ```
   pip3 install -r requirements.txt
   ```

4. 打补丁。

   ```
   patch -p0 < fix.patch
   ```

## 准备数据集<a name="section183221994411"></a>

1. 获取原始数据集。（解压命令参考tar –xvf  \*.tar与 unzip \*.zip）

   本模型支持处理后的UCF101验证集，用户需自行获取处理后的数据集（[下载链接](https://sites.google.com/view/xiangyuxu/qvi_nips19)），将文件解压并上传数据集到任意路径下。数据集目录结构如下：

   ```
   ucf101_extracted
   ├── 0
   	├── frame0.png         
   	├── frame1.png  
   	├── frame2.png          
   	├── frame3.png
       └── frame4.png        
   ├── 1 
   ├── 2   
   ......
   └── 99
   ```

2. 数据预处理，将原始数据集转换为模型输入的数据。

   执行 FLAVR_preprocess.py 脚本，完成预处理。

   ```
   python3 FLAVR_preprocess.py --data_dir ${data_dir} --save_dir ${save_dir} 
   ```
   参数说明：

   - --data_dir：原数据集所在路径。
   - --save_dir：生成数据集二进制文件。


## 模型推理<a name="section741711594517"></a>

1. 模型转换。

   使用PyTorch将模型权重文件.pth转换为.onnx文件，再使用ATC工具将.onnx文件转为离线推理模型文件.om文件。

   1. 获取权重文件。

       从开源仓获取权重文件[FLAVR_4x.pth](https://drive.google.com/file/d/1btmNm4LkHVO9gjAaKKN9CXf5vP7h4hCy/view?usp=sharing)

   2. 导出onnx文件。

      1. 使用FLAVR_pth2onnx.py导出onnx文件。

         ```
         python3 FLAVR_pth2onnx.py --input_file FLAVR_4x.pth --output_file FLAVR_4x.onnx
         ```

         获得FLAVR_4x.onnx文件。

         参数说明：

         - --input_file：权重文件。
         - --output_file：生成 onnx 文件。

      2. 优化ONNX文件。

         ```
         python3 -m onnxsim FLAVR_4x.onnx FLAVR_4x_bs${bs}_sim.onnx \
         --overwrite-input-shape "input_0:${bs},3,224,224" "input_1:${bs},3,224,224" "input_2:${bs},3,224,224" "input_3:${bs},3,224,224" 
         ```
         
         获得简化后的onnx文件，其中\${bs}为批次大小。
         
         参数说明：
         
         - --overwrite-input-shape：模型输入的维度信息。

   3. 使用ATC工具将ONNX模型转OM模型（以bs=8为例）。

      1. 配置环境变量。

         ```
          source /usr/local/Ascend/ascend-toolkit/set_env.sh
         ```

      2. 执行命令查看芯片名称（$\{chip\_name\}）。

         ```
         npu-smi info
         #该设备芯片名为Ascend310P3 （自行替换）
         回显如下：
         +-------------------+-----------------+------------------------------------------------------+
         | NPU     Name      | Health          | Power(W)     Temp(C)           Hugepages-Usage(page) |
         | Chip    Device    | Bus-Id          | AICore(%)    Memory-Usage(MB)                        |
         +===================+=================+======================================================+
         | 0       310P3     | OK              | 15.8         42                0    / 0              |
         | 0       0         | 0000:82:00.0    | 0            1074 / 21534                            |
         +===================+=================+======================================================+
         | 1       310P3     | OK              | 15.4         43                0    / 0              |
         | 0       1         | 0000:89:00.0    | 0            1070 / 21534                            |
         +===================+=================+======================================================+
         ```

      3. 执行ATC命令。

         ```
          atc --model=./FLAVR_4x_bs8_sim.onnx --framework=5 --output=FLAVR_4x_bs8 \
          --input-shape="input_0:4,3,224,224;input_1:4,3,224,224;input_2:4,3,224,224;input_3:4,3,224,224" \
          --log=error --soc_version=Ascend${chip_name}
         ```

         运行成功后生成FLAVR_4x_bs8.om模型文件。
         
         参数说明：
         - --model：为ONNX模型文件。
         - --framework：5代表ONNX模型。
         - --output：输出的OM模型。
         - --input\_format：输入数据的格式。
         - --input\_shape：输入数据的shape。
         - --log：日志级别。
         - --soc\_version：处理器型号。
         

2. 开始推理验证（以bs=8为例）。

   1. 使用ais-infer工具进行推理。

      ais-infer工具获取及使用方式请点击查看[[ais_infer 推理工具使用文档](https://gitee.com/ascend/tools/tree/master/ais-bench_workload/tool/ais_infer)]

   2. 执行推理。

      ```
      mkdir result
      python3 ${ais_infer_path}/ais_infer.py --model=FLAVR_4x_bs8.om  --batchsize=8 \
      --input ${save_dir}/input_0,${save_dir}/input_1,.${save_dir}/input_2,${save_dir}/input_3 \
      --output result --output_dirname result_bs8
      ```
        
      参数说明：
        
      -   --model：om模型路径。
      -   --batchsize：批次大小。
      -   --input：输入数据所在路径。

      >**说明：** 
      >执行ais-infer工具请选择与运行环境架构相同的命令。参数详情请参见。
        
   3. 精度验证。

      调用脚本与数据集标签val\_label.txt比对，可以获得Accuracy数据，结果保存在result.json中。

      ```
       python3 FLAVR_postprocess.py --data_dir ${data_dir} --result_dir ./result/result_bs8
      ```
   
      参数说明：

      - --data_dir：原数据集所在路径。
      - --result_dir：推理结果所在路径。
   
   4. 可使用ais_infer推理工具的纯推理模式验证不同batch_size的om模型的性能，参考命令如下：
   
      ```
      python3 ${ais_infer_path}/ais_infer.py --model=FLAVR_4x_bs${bs}.om --loop=50 --batchsize=${bs}
      ```
      
      参数说明：
      - --model：om模型路径。
      - --batchsize：批次大小。
   



# 模型推理性能&精度<a name="ZH-CN_TOPIC_0000001172201573"></a>

调用ACL接口推理计算，性能参考下列数据。

| 芯片型号    | Batch Size | 数据集 | 精度指标1（PSNR） | 精度指标2（SSIM） | 性能（FPS） |
| ----------- | ---------- | ------ | ------------ | ---- | ---- |
| Ascend310P3 | 1          | ucf101 | 29.83        | 0.9446  |  55.53    |
| Ascend310P3 | 4          | ucf101 | 29.83        | 0.9446  |  67.65    |
| Ascend310P3 | 8          | ucf101 | 29.83        | 0.9446  |  71.88    |
| Ascend310P3 | 16         | ucf101 | 29.83        | 0.9446  |   71.15   |
| Ascend310P3 | 32         | ucf101 | 29.83        | 0.9446  |   71.49   |
| Ascend310P3 | 64         | ucf101 | 29.83        | 0.9446  |    71.35  |

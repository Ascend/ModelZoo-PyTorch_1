source env_npu.sh
export WORLD_SIZE=1
rm -f nohup.out

RANK_ID=0

export RANK=$RANK_ID

nohup python3 main_finetune.py  \
    --cfg configs/swin_base__100ep/simmim_finetune__swin_base__img192_window6__100ep.yaml \
    --opts TRAIN.EPOCHS 2 \
    --pretrained ./output/simmim_pretrain/simmim_pretrain__swin_base__img192_window6__100ep/ckpt_epoch_2.pth \
    --batch-size 128 \
    --amp-opt-level O1 \
    --local_rank $RANK_ID \
    --data-path /data/imagenet &
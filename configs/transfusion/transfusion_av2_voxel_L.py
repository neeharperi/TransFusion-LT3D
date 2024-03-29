data_root = "/ssd0/nperi/Sensor/"
#data_root = "/home/ubuntu/Workspace/Data/Sensor/"

dataset_type = 'AV2Dataset'
VERSION = "av2_mmdet3d_trainval"

input_modality = dict(
    use_lidar=True,
    use_camera=False,
    use_radar=False,
    use_map=False,
    use_external=False)

SAMPLER_TYPE = "STANDARD"

voxel_size = [0.075, 0.075, 0.2]
point_cloud_range = [-54, -54, -3, 54, 54, 3]
sparse_shape = [int((abs(point_cloud_range[2]) + abs(point_cloud_range[5])) / voxel_size[2]) + 1, int((abs(point_cloud_range[1]) + abs(point_cloud_range[4])) / voxel_size[1]), int((abs(point_cloud_range[0]) + abs(point_cloud_range[3])) / voxel_size[0])]
grid_size  = [int((abs(point_cloud_range[0]) + abs(point_cloud_range[3])) / voxel_size[0]), int((abs(point_cloud_range[1]) + abs(point_cloud_range[4])) / voxel_size[1])]

file_client_args = dict(backend='disk')
CLASS_NAMES = [
    'REGULAR_VEHICLE', 'PEDESTRIAN', 'BICYCLIST', 'MOTORCYCLIST', 'WHEELED_RIDER',
    'BOLLARD', 'CONSTRUCTION_CONE', 'SIGN', 'CONSTRUCTION_BARREL', 'STOP_SIGN', 'MOBILE_PEDESTRIAN_CROSSING_SIGN',
    'LARGE_VEHICLE', 'BUS', 'BOX_TRUCK', 'TRUCK', 'VEHICULAR_TRAILER', 'TRUCK_CAB', 'SCHOOL_BUS', 'ARTICULATED_BUS',
    'MESSAGE_BOARD_TRAILER', 'BICYCLE', 'MOTORCYCLE', 'WHEELED_DEVICE', 'WHEELCHAIR', 'STROLLER', 'DOG'
]

TOTAL_CLASS_NAMES = CLASS_NAMES + ["VEHICLE", "VULNERABLE", "MOVABLE", "OBJECT"]

TASK_NAMES = {"STANDARD": ['REGULAR_VEHICLE', 'PEDESTRIAN', 'BICYCLIST', 'MOTORCYCLIST', 'WHEELED_RIDER', 'BOLLARD', 'CONSTRUCTION_CONE', 'SIGN', 'CONSTRUCTION_BARREL', 'STOP_SIGN', 
                            'MOBILE_PEDESTRIAN_CROSSING_SIGN', 'LARGE_VEHICLE', 'BUS', 'BOX_TRUCK', 'TRUCK', 'VEHICULAR_TRAILER', 'TRUCK_CAB', 'SCHOOL_BUS', 'ARTICULATED_BUS', 'MESSAGE_BOARD_TRAILER', 
                            'BICYCLE', 'MOTORCYCLE', 'WHEELED_DEVICE', 'WHEELCHAIR', 'STROLLER', 'DOG'],
              "GROUP": ["VEHICLE", "VULNERABLE", "MOVABLE"],
              "ALL" : ["OBJECT"]
             }

CLASS_MAPPING = {"STANDARD": [['REGULAR_VEHICLE'], ['PEDESTRIAN'], ['BICYCLIST'], ['MOTORCYCLIST'], ['WHEELED_RIDER'], ['BOLLARD'], ['CONSTRUCTION_CONE'], ['SIGN'], ['CONSTRUCTION_BARREL'], ['STOP_SIGN'], 
                                ['MOBILE_PEDESTRIAN_CROSSING_SIGN'], ['LARGE_VEHICLE'], ['BUS'], ['BOX_TRUCK'], ['TRUCK'], ['VEHICULAR_TRAILER'], ['TRUCK_CAB'], ['SCHOOL_BUS'], ['ARTICULATED_BUS'], ['MESSAGE_BOARD_TRAILER'], 
                                ['BICYCLE'], ['MOTORCYCLE'], ['WHEELED_DEVICE'], ['WHEELCHAIR'], ['STROLLER'], ['DOG']],
                 "GROUP" : [['REGULAR_VEHICLE', 'LARGE_VEHICLE', 'BUS', 'BOX_TRUCK', 'TRUCK', 'VEHICULAR_TRAILER', 'TRUCK_CAB', 'SCHOOL_BUS', 'ARTICULATED_BUS'], 
                            ['PEDESTRIAN', 'WHEELED_RIDER', 'BICYCLE', 'MOTORCYCLE', 'BICYCLIST', 'MOTORCYCLIST', 'WHEELED_DEVICE', 'WHEELCHAIR', 'STROLLER', 'DOG'], 
                            ['BOLLARD', 'CONSTRUCTION_CONE', 'SIGN', 'CONSTRUCTION_BARREL', 'STOP_SIGN', 'MOBILE_PEDESTRIAN_CROSSING_SIGN', 'MESSAGE_BOARD_TRAILER']],
                 "ALL" : [['REGULAR_VEHICLE', 'PEDESTRIAN', 'BICYCLIST', 'MOTORCYCLIST', 'WHEELED_RIDER', 'BOLLARD', 'CONSTRUCTION_CONE', 'SIGN', 'CONSTRUCTION_BARREL', 'STOP_SIGN', 
                                'MOBILE_PEDESTRIAN_CROSSING_SIGN', 'LARGE_VEHICLE', 'BUS', 'BOX_TRUCK', 'TRUCK', 'VEHICULAR_TRAILER', 'TRUCK_CAB', 'SCHOOL_BUS', 'ARTICULATED_BUS', 'MESSAGE_BOARD_TRAILER', 
                                'BICYCLE', 'MOTORCYCLE', 'WHEELED_DEVICE', 'WHEELCHAIR', 'STROLLER', 'DOG']]
                 }

out_size_factor = 8

input_modality = dict(
    use_lidar=True,
    use_camera=False,
    use_radar=False,
    use_map=False,
    use_external=False)

model = dict(
    type='TransFusionDetector',
    pts_voxel_layer=dict(
        max_num_points=10,
        voxel_size=voxel_size,
        max_voxels=(120000, 160000),
        point_cloud_range=point_cloud_range),
    pts_voxel_encoder=dict(
        type='HardSimpleVFE',
        num_features=6,
    ),
    pts_middle_encoder=dict(
        type='SparseEncoder',
        in_channels=6,
        sparse_shape=sparse_shape,
        output_channels=128,
        order=('conv', 'norm', 'act'),
        encoder_channels=((16, 16, 32), (32, 32, 64), (64, 64, 128), (128, 128)),
        encoder_paddings=((0, 0, 1), (0, 0, 1), (0, 0, [0, 1, 1]), (0, 0)),
        block_type='basicblock'),
    pts_backbone=dict(
        type='SECOND',
        in_channels=128,
        out_channels=[128, 256],
        layer_nums=[5, 5],
        layer_strides=[1, 2],
        norm_cfg=dict(type='BN', eps=0.001, momentum=0.01),
        conv_cfg=dict(type='Conv2d', bias=False)),
    pts_neck=dict(
        type='SECONDFPN',
        in_channels=[128, 256],
        out_channels=[256, 256],
        upsample_strides=[1, 2],
        norm_cfg=dict(type='BN', eps=0.001, momentum=0.01),
        upsample_cfg=dict(type='deconv', bias=False),
        use_conv_for_no_stride=True),
    pts_bbox_head=dict(
        type='TransFusionHead',
        num_proposals=200,
        auxiliary=True,
        in_channels=256 * 2,
        hidden_channel=128,
        num_classes=len(TOTAL_CLASS_NAMES),
        num_decoder_layers=1,
        num_heads=8,
        learnable_query_pos=False,
        initialize_by_heatmap=True,
        nms_kernel_size=3,
        ffn_channel=256,
        dropout=0.1,
        bn_momentum=0.1,
        activation='relu',
        common_heads=dict(center=(2, 2), height=(1, 2), dim=(3, 2), rot=(2, 2), vel=(2, 2)),
        bbox_coder=dict(
            type='TransFusionBBoxCoder',
            pc_range=point_cloud_range[:2],
            voxel_size=voxel_size[:2],
            out_size_factor=out_size_factor,
            post_center_range=[-61.2, -61.2, -10.0, 61.2, 61.2, 10.0],
            score_threshold=0.0,
            code_size=10,
        ),
        loss_cls=dict(type='FocalLoss', use_sigmoid=True, gamma=2, alpha=0.25, reduction='mean', loss_weight=1.0),
        # loss_iou=dict(type='CrossEntropyLoss', use_sigmoid=True, reduction='mean', loss_weight=0.0),
        loss_bbox=dict(type='L1Loss', reduction='mean', loss_weight=0.25),
        loss_heatmap=dict(type='GaussianFocalLoss', reduction='mean', loss_weight=1.0),
    ),
    train_cfg=dict(
        pts=dict(
            dataset='AV2',
            assigner=dict(
                type='HungarianAssigner3D',
                iou_calculator=dict(type='BboxOverlaps3D', coordinate='lidar'),
                cls_cost=dict(type='FocalLossCost', gamma=2, alpha=0.25, weight=0.15),
                reg_cost=dict(type='BBoxBEVL1Cost', weight=0.25),
                iou_cost=dict(type='IoU3DCost', weight=0.25)
            ),
            pos_weight=-1,
            gaussian_overlap=0.1,
            min_radius=2,
            grid_size=grid_size,  # [x_len, y_len, 1]
            voxel_size=voxel_size,
            out_size_factor=out_size_factor,
            code_weights=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.2, 0.2],
            point_cloud_range=point_cloud_range)),
    test_cfg=dict(
        pts=dict(
            dataset='AV2',
            grid_size=grid_size,
            out_size_factor=out_size_factor,
            pc_range=point_cloud_range[0:2],
            voxel_size=voxel_size[:2],
            nms_type=None,
        )))

db_sampler = dict(
data_root=data_root,
info_path=data_root + '{}/av2_dbinfos_train.pkl'.format(VERSION),
rate=1.0,
sampler_type=SAMPLER_TYPE, 
task_names=TASK_NAMES,
class_mapping=CLASS_MAPPING,
prepare=dict(
    filter_by_difficulty=[-1],
    filter_by_min_points=dict(
        REGULAR_VEHICLE=5,
        PEDESTRIAN=5,
        BICYCLIST=5,
        MOTORCYCLIST=5,
        WHEELED_RIDER=5,
        BOLLARD=5,
        CONSTRUCTION_CONE=5,
        SIGN=5,
        CONSTRUCTION_BARREL=5,
        STOP_SIGN=5,
        MOBILE_PEDESTRIAN_CROSSING_SIGN=5,
        LARGE_VEHICLE=5,
        BUS=5,
        BOX_TRUCK=5,
        TRUCK=5,
        VEHICULAR_TRAILER=5,
        TRUCK_CAB=5,
        SCHOOL_BUS=5,
        ARTICULATED_BUS=5,
        MESSAGE_BOARD_TRAILER=5,
        BICYCLE=5,
        MOTORCYCLE=5,
        WHEELED_DEVICE=5,
        WHEELCHAIR=5,
        STROLLER=5,
        DOG=5,
        )),
classes=CLASS_NAMES,
sample_groups=dict(
    REGULAR_VEHICLE=2,
    PEDESTRIAN=2,
    BICYCLIST=5,
    MOTORCYCLIST=5,
    WHEELED_RIDER=6,
    BOLLARD=3,
    CONSTRUCTION_CONE=3,
    SIGN=4,
    CONSTRUCTION_BARREL=3,
    STOP_SIGN=3,
    MOBILE_PEDESTRIAN_CROSSING_SIGN=7,
    LARGE_VEHICLE=4,
    BUS=4,
    BOX_TRUCK=4,
    TRUCK=5,
    VEHICULAR_TRAILER=5,
    TRUCK_CAB=5,
    SCHOOL_BUS=6,
    ARTICULATED_BUS=6,
    MESSAGE_BOARD_TRAILER=7,
    BICYCLE=3,
    MOTORCYCLE=5,
    WHEELED_DEVICE=4,
    WHEELCHAIR=7,
    STROLLER=6,
    DOG=5,
    ),
points_loader=dict(
    type='LoadPointsFromFileFeather',
    coord_type='LIDAR',
    load_dim=6,
    use_dim=[0, 1, 2, 3, 4, 5],
    shift_height=False,
    use_color=False,
    file_client_args=file_client_args))


train_pipeline = [
    dict(
        type='LoadPointsFromFileFeather',
        coord_type='LIDAR',
        load_dim=6,
        use_dim=[0, 1, 2, 3, 4, 5],
        shift_height=False,
        use_color=False,
        file_client_args=file_client_args
        ),
    dict(
        type='LoadPointsFromMultiSweepsFeather',
        coord_type="LIDAR",
        sweeps_num=5,
        load_dim=6,
        use_dim=[0, 1, 2, 3, 4, 5],
        pad_empty_sweeps=True,
        remove_close=True,
        test_mode=False,
        shift_height=False,
        use_color=False,
        file_client_args=file_client_args
    ),
    dict(type='LoadAnnotations3D', with_bbox_3d=True, with_label_3d=True),
    dict(type='ObjectNameFilter', classes=CLASS_NAMES),
    dict(type='ObjectSample', db_sampler=db_sampler),
    dict(
        type='GlobalRotScaleTrans',
        rot_range=[-0.3925 * 2, 0.3925 * 2],
        scale_ratio_range=[0.9, 1.1],
        translation_std=[0.5, 0.5, 0.5]),
    dict(
        type='RandomFlip3D',
        sync_2d=False,
        flip_ratio_bev_horizontal=0.5,
        flip_ratio_bev_vertical=0.5),
    dict(type='ObjectNameExpansion', classes=CLASS_NAMES, task_names=TASK_NAMES, class_mapping=CLASS_MAPPING),
    dict(type='PointsRangeFilter', point_cloud_range=point_cloud_range),
    dict(type='ObjectRangeFilter', point_cloud_range=point_cloud_range),
    dict(type='ObjectNameFilter', classes=TOTAL_CLASS_NAMES),
    dict(type='PointShuffle'),
    dict(type='DefaultFormatBundle3D', class_names=TOTAL_CLASS_NAMES),
    dict(type='Collect3D', keys=['points', 'gt_bboxes_3d', 'gt_labels_3d'])
]

test_pipeline = [
    dict(
        type='LoadPointsFromFileFeather',
        coord_type='LIDAR',
        load_dim=6,
        use_dim=[0, 1, 2, 3, 4, 5],
        shift_height=False,
        use_color=False,
        file_client_args=file_client_args
    ),
    dict(
        type='LoadPointsFromMultiSweepsFeather',
        coord_type="LIDAR",
        sweeps_num=5,
        load_dim=6,
        use_dim=[0, 1, 2, 3, 4, 5],
        pad_empty_sweeps=True,
        remove_close=True,
        test_mode=False,
        shift_height=False,
        use_color=False,
        file_client_args=file_client_args
    ),
    dict(
        type='MultiScaleFlipAug3D',
        img_scale=(1333, 800),
        pts_scale_ratio=1,
        flip=False,
        transforms=[
            dict(
                type='GlobalRotScaleTrans',
                rot_range=[0, 0],
                scale_ratio_range=[1.0, 1.0],
                translation_std=[0, 0, 0]),
            dict(type='RandomFlip3D'),
            dict(
                type='PointsRangeFilter', point_cloud_range=point_cloud_range),
            dict(
                type='DefaultFormatBundle3D',
                class_names=CLASS_NAMES,
                with_label=False),
            dict(type='Collect3D', keys=['points'])
        ])
]

data = dict(
    samples_per_gpu=1,
    workers_per_gpu=4,
    train=dict(
        type='CBGSDataset',
        dataset=dict(
            type=dataset_type,
            data_root=data_root,
            ann_file=data_root + '{}/av2_infos_train.pkl'.format(VERSION),
            pipeline=train_pipeline,
            classes=CLASS_NAMES,
            modality=input_modality,
            test_mode=False,
            box_type_3d='LiDAR')),
    val=dict(
        type=dataset_type,
        data_root=data_root,
        ann_file=data_root + '{}/av2_infos_val.pkl'.format(VERSION),
        pipeline=test_pipeline,
        classes=CLASS_NAMES,
        modality=input_modality,
        test_mode=True,
        box_type_3d='LiDAR'),
    test=dict(
        type=dataset_type,
        data_root=data_root,
        ann_file=data_root + '{}/av2_infos_val.pkl'.format(VERSION),
        pipeline=test_pipeline,
        classes=CLASS_NAMES,
        modality=input_modality,
        test_mode=True,
        box_type_3d='LiDAR'))


eval_pipeline = [
    dict(
        type='LoadPointsFromFile',
        coord_type='LIDAR',
        load_dim=5,
        use_dim=5,
        file_client_args=file_client_args),
    dict(
        type='LoadPointsFromMultiSweeps',
        sweeps_num=9,
        use_dim=[0, 1, 2, 3, 4],
        file_client_args=file_client_args,
        pad_empty_sweeps=True,
        remove_close=True),
    dict(
        type='DefaultFormatBundle3D',
        class_names=CLASS_NAMES,
        with_label=False),
    dict(type='Collect3D', keys=['points'])
]

evaluation = dict(interval=20, pipeline=eval_pipeline)

optimizer = dict(type='AdamW', lr=0.0001, weight_decay=0.01)  # for 8gpu * 2sample_per_gpu
optimizer_config = dict(grad_clip=dict(max_norm=0.1, norm_type=2))
lr_config = dict(
    policy='cyclic',
    target_ratio=(10, 0.0001),
    cyclic_times=1,
    step_ratio_up=0.4)
momentum_config = dict(
    policy='cyclic',
    target_ratio=(0.8947368421052632, 1),
    cyclic_times=1,
    step_ratio_up=0.4)

total_epochs = 20
# disable opencv multithreading to avoid system being overloaded
opencv_num_threads = 0
# set multi-process start method as `fork` to speed up the training
mp_start_method = 'fork'

# runtime settings
runner = dict(type='EpochBasedRunner', max_epochs=total_epochs)

checkpoint_config = dict(interval=1)
log_config = dict(
    interval=50,
    hooks=[dict(type='TextLoggerHook'),
           dict(type='TensorboardLoggerHook')])
dist_params = dict(backend='nccl')
log_level = 'INFO'
work_dir = None
load_from = None
resume_from = None
workflow = [('train', 1)]
gpu_ids = range(0, 8)

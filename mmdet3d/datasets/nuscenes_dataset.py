import mmcv
import numpy as np
import pyquaternion
import tempfile
from nuscenes.utils.data_classes import Box as NuScenesBox
from os import path as osp

from mmdet.datasets import DATASETS
from ..core import show_result
from ..core.bbox import Box3DMode, Coord3DMode, LiDARInstance3DBoxes, get_box_type
from .custom_3d import Custom3DDataset

from nuscenes.eval.detection.constants import DETECTION_NAMES
from nuscenes import NuScenes
from torch.utils.data import Dataset
import pandas as pd

def distance_matrix(A, B, squared=False):
    M = A.shape[0]
    N = B.shape[0]
    assert A.shape[1] == B.shape[1], f"The number of components for vectors in A \
        {A.shape[1]} does not match that of B {B.shape[1]}!"
    A_dots = (A*A).sum(axis=1).reshape((M,1))*np.ones(shape=(1,N))
    B_dots = (B*B).sum(axis=1)*np.ones(shape=(M,1))
    D_squared =  A_dots + B_dots -2*A.dot(B.T)
    if squared == False:
        zero_mask = np.less(D_squared, 0.0)
        D_squared[zero_mask] = 0.0
        return np.sqrt(D_squared)
    return D_squared
def box_center(boxes):
    center_box = np.array([box["translation"][:2] for box in boxes])
    return center_box

@DATASETS.register_module()
class NuScenesDataset(Custom3DDataset):
    r"""NuScenes Dataset.

    This class serves as the API for experiments on the NuScenes Dataset.

    Please refer to `NuScenes Dataset <https://www.nuscenes.org/download>`_
    for data downloading.

    Args:
        ann_file (str): Path of annotation file.
        pipeline (list[dict], optional): Pipeline used for data processing.
            Defaults to None.
        data_root (str): Path of dataset root.
        classes (tuple[str], optional): Classes used in the dataset.
            Defaults to None.
        load_interval (int, optional): Interval of loading the dataset. It is
            used to uniformly sample the dataset. Defaults to 1.
        with_velocity (bool, optional): Whether include velocity prediction
            into the experiments. Defaults to True.
        modality (dict, optional): Modality to specify the sensor data used
            as input. Defaults to None.
        box_type_3d (str, optional): Type of 3D box of this dataset.
            Based on the `box_type_3d`, the dataset will encapsulate the box
            to its original format then converted them to `box_type_3d`.
            Defaults to 'LiDAR' in this dataset. Available options includes.
            - 'LiDAR': Box in LiDAR coordinates.
            - 'Depth': Box in depth coordinates, usually for indoor dataset.
            - 'Camera': Box in camera coordinates.
        filter_empty_gt (bool, optional): Whether to filter empty GT.
            Defaults to True.
        test_mode (bool, optional): Whether the dataset is in test mode.
            Defaults to False.
        eval_version (bool, optional): Configuration version of evaluation.
            Defaults to  'detection_lt3d'.
        use_valid_flag (bool): Whether to use `use_valid_flag` key in the info
            file as mask to filter gt_boxes and gt_names. Defaults to False.
    """
    NameMapping = {
        "human.pedestrian.adult": "adult",
        "human.pedestrian.child": "child",
        "human.pedestrian.stroller": "stroller",
        "human.pedestrian.personal_mobility": "personal_mobility",
        "human.pedestrian.police_officer": "police_officer",
        "human.pedestrian.construction_worker": "construction_worker",
        "vehicle.car": "car",
        "vehicle.motorcycle": "motorcycle",
        "vehicle.bicycle": "bicycle",
        "vehicle.bus.bendy": "bus",
        "vehicle.bus.rigid": "bus",
        "vehicle.truck": "truck",
        "vehicle.construction": "construction_vehicle",
        "vehicle.emergency.ambulance": "emergency_vehicle",
        "vehicle.emergency.police": "emergency_vehicle",
        "vehicle.trailer": "trailer",
        "movable_object.barrier": "barrier",
        "movable_object.trafficcone": "traffic_cone",
        "movable_object.pushable_pullable": "pushable_pullable",
        "movable_object.debris": "debris",
    }
    DefaultAttribute = {
        'pedestrian': 'pedestrian.moving',
        'trailer': 'vehicle.parked',
        'truck': 'vehicle.parked',
        'bus': 'vehicle.moving',
        'construction_vehicle': 'vehicle.parked',
        'barrier': '',
        'traffic_cone': '',
        "adult" : 'pedestrian.moving',
        "child" : 'pedestrian.moving',
        "stroller" : '',
        "personal_mobility" : '',
        "police_officer" : 'pedestrian.moving',
        "construction_worker" : 'pedestrian.moving',
        "car" : 'vehicle.parked',
        "motorcycle" : 'cycle.without_rider',
        "bicycle" : 'cycle.without_rider',
        "bus" : 'vehicle.moving',
        "truck" : 'vehicle.parked',
        "construction_vehicle" : 'vehicle.parked',
        "emergency_vehicle" : 'vehicle.parked',
        "trailer" : 'vehicle.parked',
        "barrier" : '',
        "traffic_cone" : '',
        "pushable_pullable" : '',
        "debris" : '',
    }
    AttrMapping = {
        'cycle.with_rider': 0,
        'cycle.without_rider': 1,
        'pedestrian.moving': 2,
        'pedestrian.standing': 3,
        'pedestrian.sitting_lying_down': 4,
        'vehicle.moving': 5,
        'vehicle.parked': 6,
        'vehicle.stopped': 7,
    }
    AttrMapping_rev = [
        'cycle.with_rider',
        'cycle.without_rider',
        'pedestrian.moving',
        'pedestrian.standing',
        'pedestrian.sitting_lying_down',
        'vehicle.moving',
        'vehicle.parked',
        'vehicle.stopped',
    ]
    # https://github.com/nutonomy/nuscenes-devkit/blob/57889ff20678577025326cfc24e57424a829be0a/python-sdk/nuscenes/eval/detection/evaluate.py#L222 # noqa
    ErrNameMapping = {
        'trans_err': 'mATE',
        'scale_err': 'mASE',
        'orient_err': 'mAOE',
        'vel_err': 'mAVE',
        'attr_err': 'mAAE'
    }
    CLASSES = ('car', 'truck', 'trailer', 'bus', 'construction_vehicle', 'bicycle', 'motorcycle', 'emergency_vehicle',
               'adult', 'child', 'police_officer', 'construction_worker', 'stroller', 'personal_mobility', 
               'pushable_pullable', 'debris', 'traffic_cone', 'barrier')

    def __init__(self,
                 ann_file,
                 num_views=6,
                 pipeline=None,
                 data_root=None,
                 classes=None,
                 load_interval=1,
                 with_velocity=True,
                 modality=None,
                 box_type_3d='LiDAR',
                 filter_empty_gt=True,
                 test_mode=False,
                 eval_version='detection_lt3d',
                 use_valid_flag=False,
                 sampler_type=None,
                 task_names=None,
                 class_mapping=None):
        self.load_interval = load_interval
        self.use_valid_flag = use_valid_flag
        super().__init__(
            data_root=data_root,
            ann_file=ann_file,
            pipeline=pipeline,
            classes=classes,
            modality=modality,
            box_type_3d=box_type_3d,
            filter_empty_gt=filter_empty_gt,
            test_mode=test_mode)

        self.sampler_type=sampler_type
        self.task_names=task_names
        self.class_mapping=class_mapping
        
        self.num_views = num_views
        assert self.num_views <= 6
        self.with_velocity = with_velocity
        self.eval_version = eval_version
        from nuscenes.eval.detection.config import config_factory
        self.eval_detection_configs = config_factory(self.eval_version)
        if self.modality is None:
            self.modality = dict(
                use_camera=False,
                use_lidar=True,
                use_radar=False,
                use_map=False,
                use_external=False,
            )

    def get_cat_ids(self, idx):
        """Get category distribution of single scene.

        Args:
            idx (int): Index of the data_info.

        Returns:
            dict[list]: for each category, if the current scene
                contains such boxes, store a list containing idx,
                otherwise, store empty list.
        """
        info = self.data_infos[idx]
        if self.use_valid_flag:
            mask = info['valid_flag']
            gt_names = set(info['gt_names'][mask])
        else:
            gt_names = set(info['gt_names'])

        cat_ids = []
        for name in gt_names:
            if name in self.CLASSES:
                cat_ids.append(self.cat2id[name])
        return cat_ids

    def load_annotations(self, ann_file):
        """Load annotations from ann_file.

        Args:
            ann_file (str): Path of the annotation file.

        Returns:
            list[dict]: List of annotations sorted by timestamps.
        """
        data = mmcv.load(ann_file)
        data_infos = list(sorted(data['infos'], key=lambda e: e['timestamp']))
        data_infos = data_infos[::self.load_interval]
        self.metadata = data['metadata']
        self.version = self.metadata['version']
        return data_infos

    def get_data_info(self, index):
        """Get data info according to the given index.

        Args:
            index (int): Index of the sample data to get.

        Returns:
            dict: Data information that will be passed to the data \
                preprocessing pipelines. It includes the following keys:

                - sample_idx (str): Sample index.
                - pts_filename (str): Filename of point clouds.
                - sweeps (list[dict]): Infos of sweeps.
                - timestamp (float): Sample timestamp.
                - img_filename (str, optional): Image filename.
                - lidar2img (list[np.ndarray], optional): Transformations \
                    from lidar to different cameras.
                - ann_info (dict): Annotation info.
        """
        info = self.data_infos[index]
        # standard protocal modified from SECOND.Pytorch
        input_dict = dict(
            sample_idx=info['token'],
            pts_filename=info['lidar_path'],
            sweeps=info['sweeps'],
            timestamp=info['timestamp'] / 1e6,
        )

        cam_orders = ['CAM_FRONT_LEFT', 'CAM_FRONT', 'CAM_FRONT_RIGHT', 'CAM_BACK_RIGHT', 'CAM_BACK', 'CAM_BACK_LEFT']
        if self.modality['use_camera']:
            image_paths = []
            lidar2img_rts = []
            # for cam_type, cam_info in info['cams'].items():
            for cam_type in cam_orders:
                cam_info = info['cams'][cam_type]
                image_paths.append(cam_info['data_path'])
                # obtain lidar to image transformation matrix
                lidar2cam_r = np.linalg.inv(cam_info['sensor2lidar_rotation'])
                lidar2cam_t = cam_info[
                    'sensor2lidar_translation'] @ lidar2cam_r.T
                lidar2cam_rt = np.eye(4)
                lidar2cam_rt[:3, :3] = lidar2cam_r.T
                lidar2cam_rt[3, :3] = -lidar2cam_t
                intrinsic = cam_info['cam_intrinsic']
                viewpad = np.eye(4)
                viewpad[:intrinsic.shape[0], :intrinsic.shape[1]] = intrinsic
                lidar2img_rt = (viewpad @ lidar2cam_rt.T)
                lidar2img_rts.append(lidar2img_rt)

            input_dict.update(
                dict(
                    img_filename=image_paths,
                    lidar2img=lidar2img_rts,
                ))

        if not self.test_mode:
            annos = self.get_ann_info(index)
            input_dict['ann_info'] = annos

        return input_dict

    def get_ann_info(self, index):
        """Get annotation info according to the given index.

        Args:
            index (int): Index of the annotation data to get.

        Returns:
            dict: Annotation information consists of the following keys:

                - gt_bboxes_3d (:obj:`LiDARInstance3DBoxes`): \
                    3D ground truth bboxes
                - gt_labels_3d (np.ndarray): Labels of ground truths.
                - gt_names (list[str]): Class names of ground truths.
        """
        info = self.data_infos[index]
        # filter out bbox containing no points
        if self.use_valid_flag:
            mask = info['valid_flag']
        else:
            mask = info['num_lidar_pts'] > 0
        gt_bboxes_3d = info['gt_boxes'][mask]
        gt_names_3d = info['gt_names'][mask]
        gt_labels_3d = []
        for cat in gt_names_3d:
            if cat in self.CLASSES:
                gt_labels_3d.append(self.CLASSES.index(cat))
            else:
                gt_labels_3d.append(-1)
        gt_labels_3d = np.array(gt_labels_3d)

        if self.with_velocity:
            gt_velocity = info['gt_velocity'][mask]
            nan_mask = np.isnan(gt_velocity[:, 0])
            gt_velocity[nan_mask] = [0.0, 0.0]
            gt_bboxes_3d = np.concatenate([gt_bboxes_3d, gt_velocity], axis=-1)

        # the nuscenes box center is [0.5, 0.5, 0.5], we change it to be
        # the same as KITTI (0.5, 0.5, 0)
        gt_bboxes_3d = LiDARInstance3DBoxes(
            gt_bboxes_3d,
            box_dim=gt_bboxes_3d.shape[-1],
            origin=(0.5, 0.5, 0.5)).convert_to(self.box_mode_3d)

        anns_results = dict(
            gt_bboxes_3d=gt_bboxes_3d,
            gt_labels_3d=gt_labels_3d,
            gt_names=gt_names_3d)
        return anns_results

    def multimodal_filter(self, predictions, rgb):
        dist_th = 8
        tokens = predictions["results"].keys()
        filter_classes = ['truck', 'trailer', 'bus', 'construction_vehicle', 'bicycle', 'motorcycle', 'emergency_vehicle', 'child', 'police_officer', 'construction_worker', 'stroller', 'personal_mobility', 'pushable_pullable', 'debris'] 
        for sample_token in tokens:
            lidar = predictions["results"][sample_token]
            rgb = rgb["results"][sample_token]
            filter_lidar = []
            for name in CLASSES:
                ld = [d for d in lidar if d["detection_name"] == name]
                
                if name in filter_classes:
                    rd = [d for d in rgb if d["detection_name"] == name]
                    anchor_center = box_center(rd)
                    group_center = box_center(ld)
                    if len(anchor_center) == 0 or len(group_center) == 0:
                        continue 
                    
                    dist_mat = distance_matrix(anchor_center, group_center)
                    dist = np.min(dist_mat, axis=0)
                    for box, dst in zip(ld, dist):
                        if dst < dist_th:
                            filter_lidar.append(box)
                else:
                    filter_lidar += list(np.array(ld))
            predictions["results"][sample_token] = filter_lidar
            return predictions
        
    def _format_bbox(self, results, jsonfile_prefix=None, filter=None):
        """Convert the results to the standard format.

        Args:
            results (list[dict]): Testing results of the dataset.
            jsonfile_prefix (str): The prefix of the output jsonfile.
                You can specify the output directory/filename by
                modifying the jsonfile_prefix. Default: None.

        Returns:
            str: Path of the output json file.
        """
        nusc_annos = {}
        mapped_class_names = self.CLASSES

        print('Start to convert detection format...')
        for sample_id, det in enumerate(mmcv.track_iter_progress(results)):
            annos = []
            boxes = output_to_nusc_box(det)
            sample_token = self.data_infos[sample_id]['token']
            boxes = lidar_nusc_box_to_global(self.data_infos[sample_id], boxes,
                                             mapped_class_names,
                                             self.eval_detection_configs,
                                             self.eval_version)
            for i, box in enumerate(boxes):
                name = mapped_class_names[box.label]
                if np.sqrt(box.velocity[0]**2 + box.velocity[1]**2) > 0.2:
                    if name in [
                            'car',
                            'construction_vehicle',
                            'bus',
                            'truck',
                            'trailer',
                    ]:
                        attr = 'vehicle.moving'
                    elif name in ['bicycle', 'motorcycle']:
                        attr = 'cycle.with_rider'
                    else:
                        attr = NuScenesDataset.DefaultAttribute[name]
                else:
                    if name in ['pedestrian']:
                        attr = 'pedestrian.standing'
                    elif name in ['bus']:
                        attr = 'vehicle.stopped'
                    else:
                        attr = NuScenesDataset.DefaultAttribute[name]

                nusc_anno = dict(
                    sample_token=sample_token,
                    translation=box.center.tolist(),
                    size=box.wlh.tolist(),
                    rotation=box.orientation.elements.tolist(),
                    velocity=box.velocity[:2].tolist(),
                    detection_name=name,
                    detection_score=box.score,
                    attribute_name=attr)
                annos.append(nusc_anno)
            nusc_annos[sample_token] = annos
        nusc_submissions = {
            'meta': self.modality,
            'results': nusc_annos,
        }

        if filter is not None: 
            rgb = json.load(open(filter, "r"))
            nusc_submissions = self.multimodal_filter(nusc_submissions, rgb)
            
        mmcv.mkdir_or_exist(jsonfile_prefix)
        res_path = osp.join(jsonfile_prefix, 'results_nusc.json')
        print('Results writes to', res_path)
        mmcv.dump(nusc_submissions, res_path)
        
        return res_path

    def _evaluate_single(self,
                         result_path,
                         out_path, 
                         metric_type="standard"):
        """Evaluation for a single model in nuScenes protocol.

        Args:
            result_path (str): Path of the result file.
            logger (logging.Logger | str | None): Logger used for printing
                related information during evaluation. Default: None.
            metric (str): Metric name used for evaluation. Default: 'bbox'.
            result_name (str): Result name in the metric prefix.
                Default: 'pts_bbox'.

        Returns:
            dict: Dictionary of evaluation details.
        """
        from nuscenes import NuScenes
        from nuscenes.eval.detection.evaluate import NuScenesEval

        output_dir = osp.join(*osp.split(result_path)[:-1])
        nusc = NuScenes(
            version=self.version, dataroot=self.data_root, verbose=False)
        eval_set_map = {
            'v1.0-mini': 'mini_val',
            'v1.0-trainval': 'val',
        }
        nusc_eval = NuScenesEval(
            nusc,
            config=self.eval_detection_configs,
            result_path=result_path,
            eval_set=eval_set_map[self.version],
            output_dir=output_dir,
            metric_type=metric_type,
            verbose=False)
        nusc_eval.main(render_curves=False)

        # record metrics
        metrics = mmcv.load(osp.join(output_dir, 'metrics_summary.json'))
        
        if metric_type == "standard":
            detection_metrics = {"trans_err" : "ATE",
                        "scale_err" : "ASE",
                        "orient_err" : "AOE", 
                        "vel_err" : "AVE",
                        "attr_err" : "AAE"}
            detection_dataFrame = { "CLASS" : [],
                                "mAP" : [],
                                "ATE" : [],
                                "ASE" : [],
                                "AOE" : [],
                                "AVE" : [],
                                "AAE" : [],
                                "NDS" : [],
                            }
            detection_dataFrame["CLASS"] = detection_dataFrame["CLASS"] + DETECTION_NAMES
            for classname in detection_dataFrame["CLASS"]:
                detection_dataFrame["mAP"].append(metrics["mean_dist_aps"][classname])
                
            classMetrics = metrics["label_tp_errors"]
            for metric in detection_metrics.keys():
                for classname in detection_dataFrame["CLASS"]:
                    detection_dataFrame[detection_metrics[metric]].append(classMetrics[classname][metric])
            for classname in detection_dataFrame["CLASS"]:
                ap = metrics["mean_dist_aps"][classname]
                tp, tp_cnt = 0, 0
                for metric in detection_metrics.keys():
                    val = metrics["label_tp_errors"][classname][metric]
                    if not np.isnan(val):
                        tp = tp + (1 - min(val, 1))
                        tp_cnt = tp_cnt + 1
                detection_dataFrame["NDS"].append((1 / (5 + tp_cnt)) * (5 * ap + tp))
        elif metric_type == "hierarchy":
            detection_dataFrame = { "CLASS" : [],
                                "LCA0" : [],
                                "LCA1" : [],
                                "LCA2" : [],
                            }
            detection_dataFrame["CLASS"] = detection_dataFrame["CLASS"] + DETECTION_NAMES
            for classname in detection_dataFrame["CLASS"]:
                aps = metrics["label_aps"][classname]
                l0 = [aps["0.5/0"], aps["1.0/0"], aps["2.0/0"], aps["4.0/0"]]
                l1 = [aps["1.0/1"], aps["0.5/1"], aps["2.0/1"], aps["4.0/1"]]
                l2 = [aps["0.5/2"], aps["1.0/2"], aps["2.0/2"], aps["4.0/2"]]
                
                detection_dataFrame["LCA0"].append(np.mean(l0))
                detection_dataFrame["LCA1"].append(np.mean(l1))
                detection_dataFrame["LCA2"].append(np.mean(l2))
        else:
            assert False, "{} is Invalid".format(metric_type)
        detection_dataFrame = pd.DataFrame.from_dict(detection_dataFrame)
        detection_dataFrame.to_csv(out_path + "/" + "nus_" + metric_type + ".csv", index=False)
        
        detail = dict()
        metric_prefix = f'pts_bbox_NuScenes'
        for name in self.CLASSES:
            for k, v in metrics['label_aps'][name].items():
                val = float('{:.4f}'.format(v))
                detail['{}/{}_AP_dist_{}'.format(metric_prefix, name, k)] = val
            for k, v in metrics['label_tp_errors'][name].items():
                val = float('{:.4f}'.format(v))
                detail['{}/{}_{}'.format(metric_prefix, name, k)] = val

        detail['{}/NDS'.format(metric_prefix)] = metrics['nd_score']
        detail['{}/mAP'.format(metric_prefix)] = metrics['mean_ap']
        return detail

    def format_results(self, results, jsonfile_prefix=None, filter=None):
        """Format the results to json (standard format for COCO evaluation).

        Args:
            results (list[dict]): Testing results of the dataset.
            jsonfile_prefix (str | None): The prefix of json files. It includes
                the file path and the prefix of filename, e.g., "a/b/prefix".
                If not specified, a temp file will be created. Default: None.

        Returns:
            tuple: Returns (result_files, tmp_dir), where `result_files` is a \
                dict containing the json filepaths, `tmp_dir` is the temporal \
                directory created for saving json files when \
                `jsonfile_prefix` is not specified.
        """
        assert isinstance(results, list), 'results must be a list'
        assert len(results) == len(self), (
            'The length of results is not equal to the dataset len: {} != {}'.
            format(len(results), len(self)))

        if jsonfile_prefix is None:
            tmp_dir = tempfile.TemporaryDirectory()
            jsonfile_prefix = osp.join(tmp_dir.name, 'results')
        else:
            tmp_dir = None

        if not ('pts_bbox' in results[0] or 'img_bbox' in results[0]):
            result_files = self._format_bbox(results, jsonfile_prefix, filter)
        else:
            result_files = dict()
            for name in results[0]:
                print(f'\nFormating bboxes of {name}')
                results_ = [out[name] for out in results]
                tmp_file_ = osp.join(jsonfile_prefix, name)
                result_files.update(
                    {name: self._format_bbox(results_, tmp_file_, filter)})
        return result_files, tmp_dir

    def evaluate(self,
                 results,
                 out_path=None, 
                 **kwargs):
        """Evaluation in nuScenes protocol.

        Args:
            results (list[dict]): Testing results of the dataset.
            metric (str | list[str]): Metrics to be evaluated.
            logger (logging.Logger | str | None): Logger used for printing
                related information during evaluation. Default: None.
            jsonfile_prefix (str | None): The prefix of json files. It includes
                the file path and the prefix of filename, e.g., "a/b/prefix".
                If not specified, a temp file will be created. Default: None.
            show (bool): Whether to visualize.
                Default: False.
            out_dir (str): Path to save the visualization results.
                Default: None.

        Returns:
            dict[str, float]: Results of each evaluation metric.
        """
        
        metric_type = kwargs.get("metric_type", None)
        filter = kwargs.get("filter", None)
        predictions = kwargs.get("predictions", None)
        ground_truth = kwargs.get("ground_truth", None)
        
        result_files, tmp_dir = self.format_results(results, out_path, filter)

        if isinstance(result_files, dict):
            results_dict = dict()
            for name in ["pts_bbox"]:
                print('Evaluating bboxes of {}'.format(name))
                ret_dict = self._evaluate_single(result_files[name], out_path=out_path, metric_type=metric_type)
            results_dict.update(ret_dict)
        elif isinstance(result_files, str):
            results_dict = self._evaluate_single(result_files)

        if tmp_dir is not None:
            tmp_dir.cleanup()

        return results_dict

    def show(self, results, out_dir):
        """Results visualization.

        Args:
            results (list[dict]): List of bounding boxes results.
            out_dir (str): Output directory of visualization result.
        """
        for i, result in enumerate(results):
            example = self.prepare_test_data(i)
            points = example['points'][0]._data.numpy()
            data_info = self.data_infos[i]
            pts_path = data_info['lidar_path']
            file_name = osp.split(pts_path)[-1].split('.')[0]
            # for now we convert points into depth mode
            points = Coord3DMode.convert_point(points, Coord3DMode.LIDAR,
                                               Coord3DMode.DEPTH)
            inds = result['pts_bbox']['scores_3d'] > 0.1
            gt_bboxes = self.get_ann_info(i)['gt_bboxes_3d'].tensor
            gt_bboxes = Box3DMode.convert(gt_bboxes, Box3DMode.LIDAR,
                                          Box3DMode.DEPTH)
            pred_bboxes = result['pts_bbox']['boxes_3d'][inds].tensor.numpy()
            pred_bboxes = Box3DMode.convert(pred_bboxes, Box3DMode.LIDAR,
                                            Box3DMode.DEPTH)
            show_result(points, gt_bboxes, pred_bboxes, out_dir, file_name)


def output_to_nusc_box(detection):
    """Convert the output to the box class in the nuScenes.

    Args:
        detection (dict): Detection results.

            - boxes_3d (:obj:`BaseInstance3DBoxes`): Detection bbox.
            - scores_3d (torch.Tensor): Detection scores.
            - labels_3d (torch.Tensor): Predicted box labels.

    Returns:
        list[:obj:`NuScenesBox`]: List of standard NuScenesBoxes.
    """
    box3d = detection['boxes_3d']
    scores = detection['scores_3d'].numpy()
    labels = detection['labels_3d'].numpy()

    box_gravity_center = box3d.gravity_center.numpy()
    box_dims = box3d.dims.numpy()
    box_yaw = box3d.yaw.numpy()
    # TODO: check whether this is necessary
    # with dir_offset & dir_limit in the head
    nus_box_dims = box_dims[:, [1, 0, 2]]

    box_list = []
    for i in range(len(box3d)):
        quat = pyquaternion.Quaternion(axis=[0, 0, 1], radians=box_yaw[i])
        velocity = (*box3d.tensor[i, 7:9], 0.0)
        # velo_val = np.linalg.norm(box3d[i, 7:9])
        # velo_ori = box3d[i, 6]
        # velocity = (
        # velo_val * np.cos(velo_ori), velo_val * np.sin(velo_ori), 0.0)
        box = NuScenesBox(
            box_gravity_center[i],
            nus_box_dims[i],
            quat,
            label=labels[i],
            score=scores[i],
            velocity=velocity)
        box_list.append(box)
    return box_list


def lidar_nusc_box_to_global(info,
                             boxes,
                             classes,
                             eval_configs,
                             eval_version='detection_lt3d'):
    """Convert the box from ego to global coordinate.

    Args:
        info (dict): Info for a specific sample data, including the
            calibration information.
        boxes (list[:obj:`NuScenesBox`]): List of predicted NuScenesBoxes.
        classes (list[str]): Mapped classes in the evaluation.
        eval_configs (object): Evaluation configuration object.
        eval_version (str): Evaluation version.
            Default: 'detection_lt3d'

    Returns:
        list: List of standard NuScenesBoxes in the global
            coordinate.
    """
    box_list = []
    for box in boxes:
        # Move box to ego vehicle coord system
        box.rotate(pyquaternion.Quaternion(info['lidar2ego_rotation']))
        box.translate(np.array(info['lidar2ego_translation']))
        # filter det in ego.
        cls_range_map = eval_configs.class_range
        radius = np.linalg.norm(box.center[:2], 2)

        if box.label >= len(classes):
            continue 

        det_range = cls_range_map[classes[box.label]]
        if radius > det_range:
            continue
        # Move box to global coord system
        box.rotate(pyquaternion.Quaternion(info['ego2global_rotation']))
        box.translate(np.array(info['ego2global_translation']))
        box_list.append(box)
    return box_list

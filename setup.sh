source ~/.bashrc

conda install -y -c anaconda cmake
pip install torch==1.10.1+cu111 torchvision==0.11.2+cu111 torchaudio==0.10.1 -f https://download.pytorch.org/whl/torch_stable.html

pip install mmcv-full==1.2.4 -f https://download.openmmlab.com/mmcv/dist/cu111/torch1.10.0/index.html
pip install mmdet==2.10.0

pip uninstall -y mmdet3d
rm -rf ./build
pip install -e .

pip install numba
pip install rich
pip install tensorboard
pip install shapely
pip install tqdm 
pip install pyquaternion
pip install cachetools
pip install trimesh
pip install scikit-image
pip install scikit-learn
pip install pyntcloud
pip install pyarrow
pip uninstall -y nuscenes-devkit
pip install setuptools==59.5.0
pip install nntime

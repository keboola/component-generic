import json
import os
import shutil
import sys
from pathlib import Path
from runpy import run_path
from typing import List

from configuration import convert_to_v2


def _get_testing_dirs(data_dir: str) -> List:
    """
    Gets directories within a directory that do not start with an underscore

    Args:
        data_dir: directory which holds directories

    Returns:
        list of paths inside directory
    """
    return [os.path.join(data_dir, o) for o in os.listdir(data_dir) if
            os.path.isdir(os.path.join(data_dir, o)) and not o.startswith('_')]


def run_component(component_script, data_folder):
    """
    Runs a component script with a specified parameters
    """
    os.environ["KBC_DATADIR"] = data_folder
    run_path(component_script, run_name='__main__')


test_dirs = _get_testing_dirs(Path(__file__).parent.absolute().as_posix())

v2_dir = Path(__file__).parent.joinpath('v2').absolute()

component_script = Path(__file__).absolute().parent.parent.parent.joinpath('src/component.py').as_posix()

for dir_path in test_dirs:
    if Path(dir_path).name == 'v2':
        continue
    print(f'Converting example {Path(dir_path).name}/n')
    sys.path.append(Path(component_script).parent.as_posix())
    result_dir = v2_dir.joinpath(Path(dir_path).name)
    shutil.copytree(dir_path, result_dir.as_posix(), dirs_exist_ok=True)
    # convert config
    with open(Path(dir_path).joinpath('config.json').absolute().as_posix()) as inp:
        old_cfg = json.load(inp)
        new_params = convert_to_v2(old_cfg['parameters'])
    with open(result_dir.joinpath('config.json').absolute().as_posix(), 'w+') as outp:
        old_cfg['parameters'] = new_params
        json.dump(old_cfg, outp)

print('All conversions finished successfully!')

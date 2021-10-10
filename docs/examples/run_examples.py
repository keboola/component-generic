import os
import sys
from pathlib import Path
from runpy import run_path
from typing import List


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
    Runs a component script with a specified configuration
    """
    os.environ["KBC_DATADIR"] = data_folder
    run_path(component_script, run_name='__main__')


test_dirs = _get_testing_dirs(Path(__file__).parent.absolute().as_posix())

component_script = Path(__file__).absolute().parent.parent.parent.joinpath('src/component.py').as_posix()

for dir_path in test_dirs:
    print(f'Running example {Path(dir_path).name}/n')
    sys.path.append(Path(component_script).parent.as_posix())
    run_component(component_script, dir_path)

print('All tests finished successfully!')

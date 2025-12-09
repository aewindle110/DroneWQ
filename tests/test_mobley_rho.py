import sys
import os
from pathlib import Path
import shutil
import glob
import numpy as np
import rasterio
import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from dronewq import settings
from dronewq.utils.images import load_imgs

test_path = Path(__file__).absolute().parent / "test_set"
if not test_path.exists():
    raise LookupError(f"Could not find test directory: {test_path}")

settings.configure(main_dir=test_path)

def test_mobley_rho():
    from dronewq.lw_methods.mobley_rho import mobley_rho
    results = mobley_rho(num_workers=2)
    assert results is not None, "mobley_rho returned None"
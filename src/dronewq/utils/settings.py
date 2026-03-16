"""
Created by: Temuulen
Took inspo from the DSPY package's settings
"""

import copy
import logging
import os
import pickle
from pathlib import Path

from dronewq.utils.utils import dotdict

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DEFAULT_CONFIG = dotdict(
    main_dir=None,
    output_dir=None,
    raw_water_dir=None,
    raw_sky_dir=None,
    lt_dir=None,
    sky_lt_dir=None,
    lw_dir=None,
    panel_dir=None,
    rrs_dir=None,
    masked_rrs_dir=None,
    warp_img_dir=None,
    metadata=None,
    lw_method="mobley_rho",
    pixel_masking_method=None,
    ed_method="dls_ed",
    overwrite_lt_lw=False,
    clean_intermediates=True,
)

main_thread_config = copy.deepcopy(DEFAULT_CONFIG)


class Settings:
    """
    A singleton class for the whole workflow.
    If `main_dir` is given other dependent
    directories are automatically populated.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __getattr__(self, name):
        if name in main_thread_config:
            return main_thread_config[name]
        msg = f"Settings has no attribute '{name}'."
        raise ValueError(msg)

    def __setattr__(self, name, value):
        if name in ("_instance",):
            super().__setattr__(name, value)
        else:
            self.configure(**{name: value})

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    def __contains__(self, key):
        return key in main_thread_config

    def get(self, key, default=None):
        try:
            return self[key]
        except AttributeError:
            return default

    def copy(self):
        return dotdict({**main_thread_config})

    def save(self, path: str):
        path = os.path.join(path, "settings.pkl")
        # write only the plain config dict (not the Settings instance)
        with open(path, "wb") as dst:
            pickle.dump(dict(main_thread_config), dst)

    def load(self, path: str):
        path = os.path.join(path, "settings.pkl")
        with open(path, "rb") as src:
            cfg = pickle.load(src)
        if not isinstance(cfg, dict):
            msg = "settings.pkl does not contain a valid config dict"
            raise ValueError(msg)
        # update global config in-place and return the singleton
        for k, v in cfg.items():
            main_thread_config[k] = v
        return self

    @property
    def config(self):
        """Return a copy of the global config."""
        return self.copy()

    def configure(self, **kwargs):
        """Update global config."""
        # Update global config
        for k, v in kwargs.items():
            main_thread_config[k] = v

        # If main_dir is set, automatically populate dependent dirs
        if "main_dir" in kwargs:
            main_dir = kwargs["main_dir"]
            if not isinstance(main_dir, (str, Path)):
                msg = "main_dir should be a string of path."
                raise ValueError(msg)

            main_dir = Path(main_dir)

            if not main_dir.exists():
                msg = f"{main_dir} path does not exist."
                raise LookupError(msg)

            main_thread_config["main_dir"] = main_dir
            main_thread_config["raw_water_dir"] = main_dir / "raw_water_imgs"
            raw_water_dir = settings.raw_water_dir

            if not raw_water_dir.exists():
                msg = f"{raw_water_dir} does not exist."
                raise FileNotFoundError(msg)

            main_thread_config["raw_sky_dir"] = main_dir / "raw_sky_imgs"
            main_thread_config["lt_dir"] = main_dir / "lt_imgs"
            main_thread_config["sky_lt_dir"] = main_dir / "sky_lt_imgs"
            main_thread_config["panel_dir"] = main_dir / "panel"
            main_thread_config["warp_img_dir"] = main_dir / "align_img"

        if "output_dir" in kwargs:
            output_dir = kwargs["output_dir"]
            if not isinstance(output_dir, (str, Path)):
                msg = "output_dir should be a string of path."
                raise ValueError(msg)

            output_dir = Path(output_dir)

            if not output_dir.exists():
                msg = f"{output_dir} path does not exist."
                raise LookupError(msg)

            main_thread_config["output_dir"] = output_dir
            main_thread_config["lw_dir"] = output_dir / "lw_imgs"
            main_thread_config["rrs_dir"] = output_dir / "rrs_imgs"
            main_thread_config["masked_rrs_dir"] = output_dir / "masked_rrs_imgs"
            main_thread_config["metadata"] = output_dir / "metadata.csv"
        return self


settings = Settings()

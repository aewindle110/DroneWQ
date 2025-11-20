import copy
import logging
import os
import pickle
from pathlib import Path

from dronewq.utils.utils import dotdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DEFAULT_CONFIG = dotdict(
    main_dir=None,
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
)

main_thread_config = copy.deepcopy(DEFAULT_CONFIG)


# Written by Temuulen
# Took inspo from the DSPY package's settings
class Settings:
    """
    A singleton class for the whole workflow.
    If `main_dir` is given other dependent directories are automatically populated.
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
        return self.copy()

    def configure(self, **kwargs):
        # Update global config
        for k, v in kwargs.items():
            main_thread_config[k] = v

        # If main_dir is set, automatically populate dependent dirs
        if "main_dir" in kwargs:
            if not isinstance(kwargs["main_dir"], (str, Path)):
                msg = "main_dir should be a string of path."
                raise ValueError(msg)

            if not os.path.exists(kwargs["main_dir"]):
                raise LookupError(f"{kwargs['main_dir']} path does not exist.")

            main_dir = kwargs["main_dir"]
            main_thread_config["raw_water_dir"] = os.path.join(
                main_dir,
                "raw_water_imgs",
            )
            main_thread_config["raw_sky_dir"] = os.path.join(main_dir, "raw_sky_imgs")
            main_thread_config["lt_dir"] = os.path.join(main_dir, "lt_imgs")
            main_thread_config["sky_lt_dir"] = os.path.join(main_dir, "sky_lt_imgs")
            main_thread_config["lw_dir"] = os.path.join(main_dir, "lw_imgs")
            main_thread_config["panel_dir"] = os.path.join(main_dir, "panel")
            main_thread_config["rrs_dir"] = os.path.join(main_dir, "rrs_imgs")
            main_thread_config["masked_rrs_dir"] = os.path.join(
                main_dir,
                "masked_rrs_imgs",
            )
            main_thread_config["warp_img_dir"] = os.path.join(main_dir, "align_img")
            main_thread_config["metadata"] = os.path.join(main_dir, "metadata.csv")


settings = Settings()

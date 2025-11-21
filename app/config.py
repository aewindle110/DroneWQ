from pathlib import Path


class Config(object):
    DATABASE_PATH = Path(__file__).absolute().parent.joinpath("projects.db")

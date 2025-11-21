from pathlib import Path


class Config(object):
    DATABASE_PATH = Path(__file__).parent.joinpath("projects.db")

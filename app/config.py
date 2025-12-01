from pathlib import Path


class Config:
    DATABASE_PATH = Path(__file__).absolute().parent.joinpath("projects.db")

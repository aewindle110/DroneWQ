from pathlib import Path


class Config(object):
    DATABASE_PATH = Path(__file__).absolute().parent.joinpath("projects.db")
    GEMINI_API_KEY = "AIzaSyCWeVcfvMaQ6mTZ5bdhhqQpBfwqCzMG2og"

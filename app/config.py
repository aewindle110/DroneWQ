from pathlib import Path
import os


class Config(object):
    DATABASE_PATH = Path(__file__).absolute().parent.joinpath("projects.db")

class Config:
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), "projects.db")
    GEMINI_API_KEY = "AIzaSyCWeVcfvMaQ6mTZ5bdhhqQpBfwqCzMG2og" 

import json
import sqlite3
from pathlib import Path

from config import Config


class Project:
    def __init__(
        self,
        id,
        name,
        folder_path,
        created_at,
        lw_method,
        ed_method,
        mask_method,
        mask_args,
        wq_algs,
        mosaic,
    ):
        self.id = id
        self.name = name
        self.folder_path = folder_path
        self.main_dir = folder_path
        self.data_source = Path(folder_path).name
        self.created_at = created_at
        self.lw_method = lw_method
        self.ed_method = ed_method
        self.mask_method = mask_method
        self.mask_args = json.loads(mask_args) if mask_args else {}
        self.wq_algs = json.loads(wq_algs) if wq_algs else []
        self.mosaic = mosaic

    @staticmethod
    def get_project(project_id: int):
        with sqlite3.connect(
            Config.DATABASE_PATH,
        ) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            project = c.execute(
                """
                SELECT id, name, folder_path, lw_method, ed_method, mask_method, mask_args, wq_algs, created_at, mosaic
                FROM projects
                WHERE id=?
                """,
                (project_id,),
            ).fetchone()

        if project is None:
            raise LookupError("Project not found")

        # Convert rows → JSON
        return Project(**project)

    def to_dict(self) -> dict:
        return dict(self.__dict__)

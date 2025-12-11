"""
Created by Temuulen
Simple dict class used for settings
"""

import copy


class dotdict(dict):
    def __getattr__(self, key):
        if key.startswith("__") and key.endswith("__"):
            return super().__getattr__(key)
        try:
            return self[key]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'",
            )

    def __setattr__(self, key, value) -> None:
        if key.startswith("__") and key.endswith("__"):
            super().__setattr__(key, value)
        else:
            self[key] = value

    def __delattr__(self, key) -> None:
        if key.startswith("__") and key.endswith("__"):
            super().__delattr__(key)
        else:
            del self[key]

    def __deepcopy__(self, memo) -> None:
        # Use the default dict copying method to avoid infinite recursion.
        return dotdict(copy.deepcopy(dict(self), memo))

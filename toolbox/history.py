"""Bounded undo/redo snapshots with stable revision IDs."""

from dataclasses import dataclass

import numpy as np


@dataclass
class Snapshot:
    image: np.ndarray
    label: str
    revision: int


class History:
    def __init__(self, budget=128 * 1024 * 1024, limit=20):
        self.budget, self.limit = budget, limit
        self.items = []
        self.index = -1
        self._revision = 0

    @property
    def current(self):
        return self.items[self.index] if self.items else None

    @property
    def can_undo(self):
        return self.index > 0

    @property
    def can_redo(self):
        return self.index + 1 < len(self.items)

    def reset(self, image, label="打开图像"):
        self.items.clear()
        self.index = -1
        return self.push(image, label)

    def push(self, image, label):
        del self.items[self.index + 1:]
        self._revision += 1
        self.items.append(Snapshot(image.copy(), label, self._revision))
        while len(self.items) > 1 and (len(self.items) > self.limit or sum(s.image.nbytes for s in self.items) > self.budget):
            self.items.pop(0)
        self.index = len(self.items) - 1
        return self.current

    def undo(self):
        if self.can_undo:
            self.index -= 1
        return self.current

    def redo(self):
        if self.can_redo:
            self.index += 1
        return self.current

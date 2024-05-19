from dataclasses import dataclass
from model.Object import Object

@dataclass
class Frame:
    frameId: int
    objects: list(Object)
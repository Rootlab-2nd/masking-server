from dataclasses import dataclass

@dataclass
class Object:
    objectId: int
    topLeftX: int
    topLeftY: int
    width: int
    height: int
    storagePath: str
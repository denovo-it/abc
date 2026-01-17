# Copyright Axelera AI, 2025

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Dict, Union

from .base import AxTaskMeta, MetaObject

if TYPE_CHECKING:
    from .. import display


class LicensePlateObject(MetaObject):
    @property
    def label(self):
        return self._meta.get_result()


@dataclass(frozen=True)
class LicensePlateMeta(AxTaskMeta):
    Object: ClassVar[MetaObject] = LicensePlateObject

    label: str = None

    def __len__(self):
        return 1 if self.label is not None else 0

    def add_result(self, label: str):
        object.__setattr__(self, "label", label)

    def transfer_data(self, other: LicensePlateMeta):
        """Transfer data from another LicensePlateMeta without creating intermediate copies."""
        object.__setattr__(self, "label", other.label)

    def draw(self, draw: display.Draw):
        pass

    def get_result(self):
        return self.label

    def to_evaluation(self):
        if not (ground_truth := self.access_ground_truth()):
            raise ValueError("Ground truth is not set")

        from ..eval_interfaces import LabelEvalSample, LabelGroundTruthSample

        if isinstance(ground_truth, LabelGroundTruthSample):
            return LabelEvalSample(label=self.label)
        else:
            raise NotImplementedError(
                f"Ground truth type {type(ground_truth).__name__} is not supported"
            )

    @property
    def objects(self) -> list[MetaObject]:
        return [self.label]

    @classmethod
    def decode(cls, data: Dict[str, Union[bytes, bytearray]]) -> 'LicensePlateMeta':
        label = data.get("label", b"")
        label = label.decode('utf-8')
        model_meta = cls()
        model_meta.add_result(label)
        return model_meta

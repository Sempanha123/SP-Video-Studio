from __future__ import annotations
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any

class BatchRowValidity(StrEnum): VALID="valid"; WARNING="warning"; INVALID="invalid"

@dataclass(slots=True)
class BatchInputRow:
    row_index:int; data:dict[str,Any]; validity:str|BatchRowValidity=BatchRowValidity.VALID; warnings:list[str]=field(default_factory=list); errors:list[str]=field(default_factory=list); selected:bool=True
    @property
    def validity_code(self):return self.validity.value if isinstance(self.validity,StrEnum) else str(self.validity)
    def to_dict(self):return {"rowIndex":self.row_index,"data":dict(self.data),"validity":self.validity_code,"warnings":list(self.warnings),"errors":list(self.errors),"selected":self.selected}

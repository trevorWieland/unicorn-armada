from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


class Character(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    name: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return value.strip()


class BondListEntry(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    pairs: list[str] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return value.strip()

    @field_validator("pairs", mode="before")
    @classmethod
    def normalize_pairs(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("pairs must be a list")
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            item_str = str(item).strip()
            if not item_str or item_str in seen:
                continue
            seen.add(item_str)
            cleaned.append(item_str)
        return cleaned

    @model_validator(mode="after")
    def validate_pairs(self) -> "BondListEntry":
        if self.id in self.pairs:
            raise ValueError("Bond list cannot include self in pairs")
        return self


class Dataset(BaseModel):
    characters: list[Character]
    bonds: list[BondListEntry]


class Solution(BaseModel):
    units: list[list[str]]
    unit_bonds: list[int]
    total_bonds: int
    unassigned: list[str]
    seed: int
    restarts: int
    swap_iterations: int

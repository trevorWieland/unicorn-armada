from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .utils import normalize_tag


def _normalize_tags(value: list[str] | None, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in value:
        item_str = normalize_tag(str(item))
        if not item_str or item_str in seen:
            continue
        seen.add(item_str)
        cleaned.append(item_str)
    return cleaned


def _normalize_weights(
    value: dict[str, float] | None, field_name: str
) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    cleaned: dict[str, float] = {}
    for key, weight in value.items():
        key_str = normalize_tag(str(key))
        if not key_str:
            continue
        cleaned[key_str] = float(weight)
    return cleaned


def _normalize_identifier(value: str, field_name: str) -> str:
    cleaned = normalize_tag(str(value))
    if " " in cleaned:
        raise ValueError(f"{field_name} must use underscores instead of spaces")
    return cleaned


class Character(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    name: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return value.strip()


class RapportListEntry(BaseModel):
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
    def validate_pairs(self) -> "RapportListEntry":
        if self.id in self.pairs:
            raise ValueError("Rapport list cannot include self in pairs")
        return self


class Dataset(BaseModel):
    characters: list[Character]
    rapports: list[RapportListEntry]
    classes: list["ClassDefinition"] = Field(default_factory=list)
    class_lines: list["ClassLine"] = Field(default_factory=list)
    character_classes: dict[str, "CharacterClassInfo"] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_class_references(self) -> "Dataset":
        class_ids = {entry.id for entry in self.classes}
        if len(class_ids) != len(self.classes):
            raise ValueError("Class definitions contain duplicate ids")

        line_ids = [line.id for line in self.class_lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Class lines contain duplicate ids")

        line_index = {line.id: line for line in self.class_lines}
        for line in self.class_lines:
            for class_id in line.classes:
                if class_id not in class_ids:
                    raise ValueError(
                        f"Class line {line.id} references unknown class: {class_id}"
                    )

        character_ids = {character.id for character in self.characters}
        for character_id in self.character_classes:
            if character_id not in character_ids:
                raise ValueError(
                    f"Character classes contain unknown character id: {character_id}"
                )

        for character_id, info in self.character_classes.items():
            if info.default_class not in class_ids:
                raise ValueError(
                    f"Character {character_id} references unknown class: "
                    f"{info.default_class}"
                )
            if info.class_line is None:
                continue
            line = line_index.get(info.class_line)
            if line is None:
                raise ValueError(
                    f"Character {character_id} references unknown class line: "
                    f"{info.class_line}"
                )
            if info.default_class not in line.classes:
                raise ValueError(
                    f"Character {character_id} default class {info.default_class} "
                    f"is not part of class line {info.class_line}"
                )
        return self


class LeaderEffect(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    description: Annotated[str, Field(min_length=1)]


class ClassDefinition(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    name: str | None = None
    roles: list[str]
    capabilities: list[str] = Field(default_factory=list)
    row_preference: Literal["front", "back", "flex"] = "flex"
    class_types: list[str]
    unit_type: Literal["infantry", "cavalry", "flying"]
    assist_type: Literal["none", "ranged", "magick", "healing"]
    leader_effect: LeaderEffect | None = None
    class_trait: str | None = None
    stamina: int
    mobility: int
    promotes_to: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return _normalize_identifier(str(value), "class id")

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, value: list[str] | None) -> list[str]:
        roles = _normalize_tags(value, "roles")
        if not roles:
            raise ValueError("roles must contain at least one entry")
        return roles

    @field_validator("capabilities", mode="before")
    @classmethod
    def normalize_capabilities(cls, value: list[str] | None) -> list[str]:
        return _normalize_tags(value, "capabilities")

    @field_validator("row_preference", mode="before")
    @classmethod
    def normalize_row_preference(cls, value: str | None) -> str:
        if value is None:
            return "flex"
        return normalize_tag(str(value))

    @field_validator("class_types", mode="before")
    @classmethod
    def normalize_class_types(cls, value: list[str] | None) -> list[str]:
        class_types = _normalize_tags(value, "class_types")
        if not class_types:
            raise ValueError("class_types must contain at least one entry")
        return class_types

    @field_validator("unit_type", mode="before")
    @classmethod
    def normalize_unit_type(cls, value: str) -> str:
        return normalize_tag(str(value))

    @field_validator("assist_type", mode="before")
    @classmethod
    def normalize_assist_type(cls, value: str) -> str:
        return normalize_tag(str(value))

    @field_validator("promotes_to", mode="before")
    @classmethod
    def normalize_promotes_to(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_identifier(str(value), "promotes_to")


class ClassLine(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    name: str | None = None
    classes: list[str]

    @field_validator("id", mode="before")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return _normalize_identifier(str(value), "class line id")

    @field_validator("classes", mode="before")
    @classmethod
    def normalize_classes(cls, value: list[str] | None) -> list[str]:
        class_ids = _normalize_tags(value, "classes")
        if not class_ids:
            raise ValueError("classes must contain at least one entry")
        for class_id in class_ids:
            if " " in class_id:
                raise ValueError(
                    "class line entries must use underscores instead of spaces"
                )
        return class_ids


class CharacterClassInfo(BaseModel):
    default_class: Annotated[str, Field(min_length=1)]
    class_line: str | None = None

    @field_validator("default_class", mode="before")
    @classmethod
    def normalize_default_class(cls, value: str) -> str:
        return _normalize_identifier(str(value), "default_class")

    @field_validator("class_line", mode="before")
    @classmethod
    def normalize_class_line(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_identifier(str(value), "class_line")


class CombatScoringConfig(BaseModel):
    role_weights: dict[str, float] = Field(default_factory=dict)
    capability_weights: dict[str, float] = Field(default_factory=dict)

    @field_validator("role_weights", mode="before")
    @classmethod
    def normalize_role_weights(cls, value: dict[str, float] | None) -> dict[str, float]:
        return _normalize_weights(value, "role_weights")

    @field_validator("capability_weights", mode="before")
    @classmethod
    def normalize_capability_weights(
        cls, value: dict[str, float] | None
    ) -> dict[str, float]:
        return _normalize_weights(value, "capability_weights")


class CombatUnitBreakdown(BaseModel):
    roles: dict[str, int] = Field(default_factory=dict)
    capabilities: dict[str, int] = Field(default_factory=dict)
    unknown_members: list[str] = Field(default_factory=list)
    score: float = 0.0


class CombatSummary(BaseModel):
    unit_scores: list[float] = Field(default_factory=list)
    unit_breakdowns: list[CombatUnitBreakdown] = Field(default_factory=list)
    total_score: float = 0.0


class Solution(BaseModel):
    units: list[list[str]]
    unit_rapports: list[int]
    total_rapports: int
    unassigned: list[str]
    seed: int
    restarts: int
    swap_iterations: int
    combat: CombatSummary | None = None

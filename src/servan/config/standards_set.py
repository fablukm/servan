"""StandardsSet — one standards TOML (or a merged stack) as a validated value object."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

SectionValue = str | bool | list[str]


class StandardsSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    extends: tuple[str, ...] = ()
    description: str = ""
    sections: dict[str, dict[str, SectionValue]] = {}

    def merged_over(self, base: StandardsSet) -> StandardsSet:
        """Self on top of base: scalars later-wins; string lists concat + dedupe, first wins."""
        sections = {key: dict(values) for key, values in base.sections.items()}
        for key, values in self.sections.items():
            target = sections.setdefault(key, {})
            for field, value in values.items():
                inherited = target.get(field)
                if isinstance(value, list) and isinstance(inherited, list):
                    target[field] = inherited + [rule for rule in value if rule not in inherited]
                else:
                    target[field] = value
        return StandardsSet(name=self.name, extends=self.extends,
                            description=self.description or base.description, sections=sections)

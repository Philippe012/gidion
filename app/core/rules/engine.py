from dataclasses import dataclass
from typing import Callable

from app.core.data.visit import Visit, ClassificationResult


@dataclass
class Rule:
    condition: Callable[[Visit], bool]
    classification: str
    action: str       
    section_ref: str
    action_level: int 


class RuleSet:

    def __init__(self, category: str, rules: list[Rule]):
        self.category = category
        self.rules = rules

    def evaluate(self, visit: Visit) -> ClassificationResult | None:
        for rule in self.rules:
            if rule.condition(visit):
                return ClassificationResult(
                    category=self.category,
                    classification=rule.classification,
                    action=rule.action,
                    section_ref=rule.section_ref,
                    action_level=rule.action_level,
                )
        return None
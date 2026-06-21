"""models/product_spec.py — the input to the pipeline."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ProductSpec:
    product_name: str
    category: str                    # "packaged_food" | "herbal_supplement" | "functional_food"
    ingredients: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    target_demographic: str = "adults"   # "children" | "adults" | "elderly"
    net_weight_grams: float = 0.0
    is_imported: bool = False
    packaging_material: str = ""
    country_of_origin: str = "India"
    has_herbal_ingredients: bool = False     # Quick flag for AYUSH routing
    has_health_claims: bool = False          # Quick flag for FSSAI routing

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "ProductSpec":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime
from domain.entities.research import RegimeStats


@dataclass(frozen=True)
class WalkForwardFold:
    """Represents a single train-validation split fold in the walk-forward validation pipeline."""
    fold_index: int
    train_start: datetime
    train_end: datetime
    val_start: datetime
    val_end: datetime
    train_stats: Dict[str, RegimeStats]  # Symbol -> training stats
    val_stats: Dict[str, RegimeStats]    # Symbol -> validation stats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fold_index": self.fold_index,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "val_start": self.val_start.isoformat(),
            "val_end": self.val_end.isoformat(),
            "train_stats": {k: v.to_dict() for k, v in self.train_stats.items()},
            "val_stats": {k: v.to_dict() for k, v in self.val_stats.items()}
        }


@dataclass(frozen=True)
class AlphaQualificationSession:
    """Represents the results of a complete Walk-Forward Alpha Qualification research session."""
    session_id: str
    folds: List[WalkForwardFold]
    stability_score: Decimal
    transaction_costs: Dict[str, Decimal]  # taker_fee, maker_fee, spread, slippage
    validated_features: List[str]
    rejected_features: List[str]
    cross_asset_metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "session_id": self.session_id,
            "folds": [f.to_dict() for f in self.folds],
            "stability_score": str(self.stability_score),
            "transaction_costs": {k: str(v) for k, v in self.transaction_costs.items()},
            "validated_features": self.validated_features,
            "rejected_features": self.rejected_features
        }
        if self.cross_asset_metrics is not None:
            # Recursively convert Decimals in cross_asset_metrics to strings for JSON safety
            def serialize_val(val: Any) -> Any:
                if isinstance(val, Decimal):
                    return str(val)
                elif isinstance(val, dict):
                    return {k: serialize_val(v) for k, v in val.items()}
                elif isinstance(val, list):
                    return [serialize_val(v) for v in val]
                return val
            d["cross_asset_metrics"] = serialize_val(self.cross_asset_metrics)
        return d


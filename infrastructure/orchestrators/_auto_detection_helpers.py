"""E5.T4 (infra-only mechanical split): non-trading helper methods extracted from
``AutoDetectionOrchestrator``.

Behavior-preserving mixin — methods are moved verbatim (signatures, ``self`` semantics
and outputs unchanged) and composed back into ``AutoDetectionOrchestrator`` via
inheritance. No layer move, no port inversion, no logic change.
"""
import threading


class _AutoDetectionHelpersMixin:
    """Symbol-lock management + opportunity scoring (non-trading helpers)."""

    def _get_symbol_lock(self, symbol: str) -> threading.Lock:
        """Get or create a lock for a specific symbol to prevent concurrent processing."""
        with self._symbol_processing_locks_lock:
            if symbol not in self._symbol_processing_locks:
                self._symbol_processing_locks[symbol] = threading.Lock()
            return self._symbol_processing_locks[symbol]

    def _calculate_opportunity_score(self, execution_intent) -> float:
        """Calculate a comprehensive opportunity score based on multiple factors."""
        try:
            # Base confidence score
            base_confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5

            # Get fused signal information if available
            fused_signal = getattr(execution_intent, 'fused_signal', None)
            if fused_signal:
                dominance_score = getattr(fused_signal, 'dominance_score', 0.0)
                regime_context = getattr(fused_signal, 'regime_context', 'normal')
            else:
                dominance_score = 0.0
                regime_context = 'normal'

            # Risk parameters
            risk_params = getattr(execution_intent, 'risk_parameters', {})
            position_size = risk_params.get('max_position_size', 0.02)
            stop_loss_pct = risk_params.get('stop_loss_pct', 0.02)
            take_profit_pct = risk_params.get('take_profit_pct', 0.03)

            # Calculate reward-to-risk ratio
            reward_risk_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 1.0

            # Calculate opportunity score based on multiple factors
            # Weighted combination of confidence, dominance, position size, and reward-to-risk ratio
            confidence_weight = self._settings.strategy.opportunity_score_confidence_weight if self._settings.strategy and hasattr(self._settings.strategy, 'opportunity_score_confidence_weight') else 0.4
            dominance_weight = self._settings.strategy.opportunity_score_dominance_weight if self._settings.strategy and hasattr(self._settings.strategy, 'opportunity_score_dominance_weight') else 0.2
            position_size_weight = self._settings.strategy.opportunity_score_position_size_weight if self._settings.strategy and hasattr(self._settings.strategy, 'opportunity_score_position_size_weight') else 0.15
            reward_risk_weight = self._settings.strategy.opportunity_score_reward_risk_weight if self._settings.strategy and hasattr(self._settings.strategy, 'opportunity_score_reward_risk_weight') else 0.15
            regime_bonus = self._settings.strategy.opportunity_score_regime_bonus if self._settings.strategy and hasattr(self._settings.strategy, 'opportunity_score_regime_bonus') else 0.1  # Bonus for favorable market regimes

            # Normalize values to 0-1 scale
            normalized_confidence = min(1.0, base_confidence)
            normalized_dominance = min(1.0, max(0.0, dominance_score))
            normalized_position_size = min(1.0, position_size / 0.1)  # Assuming max position size of 10%
            normalized_reward_risk = min(1.0, reward_risk_ratio / 3.0)  # Assuming max R/R of 3:1

            # Calculate base score
            base_score = (
                confidence_weight * normalized_confidence +
                dominance_weight * normalized_dominance +
                position_size_weight * normalized_position_size +
                reward_risk_weight * normalized_reward_risk
            )

            # Add regime bonus for favorable market conditions
            regime_bonus_factor = 0.0
            if regime_context.lower() in ['trending', 'breakout', 'momentum']:
                regime_bonus_factor = regime_bonus
            elif regime_context.lower() in ['volatile', 'high_volatility']:
                # Slightly reduce score for high volatility
                regime_bonus_factor = -0.05

            final_score = base_score + regime_bonus_factor

            # Ensure score is within reasonable bounds
            final_score = max(0.0, min(2.0, final_score))

            return final_score

        except Exception as e:
            self.logger.error(f"Error calculating opportunity score: {e}")
            # Return a default score in case of error
            return 0.5

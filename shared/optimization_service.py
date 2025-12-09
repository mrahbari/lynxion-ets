"""Shared optimization service with PyTorch CUDA acceleration."""

import json
import os
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from pathlib import Path

from shared.logger import EnhancedLogger

# Try to import torch, but make it optional
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # When torch is not available, we provide minimal functionality for testing
    class MockTensor:
        def __init__(self, data):
            self.data = data
        def to(self, device):
            return self
        def detach(self):
            return self
        def cpu(self):
            return self
        def numpy(self):
            return self.data if hasattr(self.data, 'numpy') else np.asarray(self.data)
        def mean(self):
            return MockTensor(np.mean(self.data))
        def std(self):
            return MockTensor(np.std(self.data))
        def sum(self):
            return MockTensor(np.sum(self.data))
        def var(self):
            return MockTensor(np.var(self.data))
        def __mul__(self, other):
            other_data = other.data if hasattr(other, 'data') else other
            return MockTensor(self.data * other_data)

    class MockDevice:
        def __init__(self, device):
            self.name = device

    class MockTorch:
        float32 = "float32"
        def tensor(self, array, dtype=None, device=None):
            return MockTensor(array)
        def device(self, device):
            return MockDevice(device)
        def cuda(self):
            return MockDevice("cuda")
        def is_available(self):
            return False

    torch = MockTorch()

# Try to import hyperopt, but make it optional
try:
    from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
    HYPEROPT_AVAILABLE = True
except ImportError:
    HYPEROPT_AVAILABLE = False
    # Define placeholders for hyperopt functions when not available
    def fmin(*args, **kwargs):
        # Return a mock result when hyperopt is not available
        space = kwargs.get('space', {})
        # Try to extract some parameters from space to show in results
        params = {}
        for key in space.keys():
            # Create mock parameter values based on hyperopt parameter types
            params[key] = 1.0  # Default mock value

        return {
            "loss": -0.1,  # Mock result
            "params": params,
            "error": "hyperopt not available - using mock results"
        }

    def tpe(*args, **kwargs):
        # Return a function that simulates algorithm behavior
        def mock_tpe(*args, **kwargs):
            pass
        return mock_tpe

    class HP:
        @staticmethod
        def quniform(low, high, q):
            import numpy as np
            # Generate a value in the range [low, high] with step q
            return np.round(np.random.uniform(low, high) / q) * q

        @staticmethod
        def uniform(low, high):
            import numpy as np
            # Generate a value in the range [low, high]
            return np.random.uniform(low, high)

        @staticmethod
        def choice(options):
            import numpy as np
            # Randomly choose from options
            if isinstance(options, list) and options:
                return options[np.random.choice(len(options))]
            return 0

        @staticmethod
        def qloguniform(low, high, q):
            import numpy as np
            # Similar to quniform but in log space
            return np.round(np.exp(np.random.uniform(np.log(low), np.log(high))) / q) * q

    hp = HP()

    def Trials():
        class MockTrials:
            def __init__(self):
                self.trials = []
                self.best_trial = {
                    'result': {
                        'loss': float('inf'),
                        'status': 'ok'
                    }
                }
            def __len__(self):
                return len(self.trials)
        return MockTrials()

    STATUS_OK = 'ok'


class OptimizationService:
    """Main optimization service with PyTorch CUDA acceleration."""
    
    def __init__(self,
                 results_dir: str = "data/optimization_results",
                 cache_dir: str = "data/optimization_cache"):
        self.results_dir = Path(results_dir)
        self.cache_dir = Path(cache_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = EnhancedLogger("OptimizationService")

        # Check CUDA availability
        if TORCH_AVAILABLE and torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu") if TORCH_AVAILABLE else "cpu"
        self.logger.info(f"Using device: {self.device}")
    
    def _to_tensor(self, array):
        """Convert numpy array to PyTorch tensor on device."""
        if isinstance(array, np.ndarray):
            return torch.tensor(array, dtype=torch.float32, device=self.device)
        return array.to(self.device)
    
    def _evaluate_strategy_gpu(self, 
                              indicators: np.ndarray, 
                              price_changes: np.ndarray, 
                              params: Dict[str, Any]) -> float:
        """GPU-accelerated strategy evaluation."""
        X = self._to_tensor(indicators)  # (N, F)
        y = self._to_tensor(price_changes)  # (N,)
        
        # Strategy weights based on params
        weights = torch.tensor([
            params.get("rsi_weight", 1.0),
            params.get("ema_fast_weight", 1.0),
            params.get("ema_slow_weight", 1.0),
            params.get("volatility_weight", 1.0)
        ], dtype=torch.float32, device=self.device)
        
        # Linear scoring
        raw_signal = torch.sum(X * weights[:X.shape[1]], dim=1)
        
        # Convert to trading signal
        signal = torch.tanh(raw_signal * params.get("signal_amplifier", 1.0))
        
        pnl = signal * y
        
        # Penalize volatility & drawdowns
        pnl_var = torch.var(pnl)
        penalty = pnl_var * params.get("variance_penalty", 0.1)
        
        score = pnl.sum() - penalty
        
        return float(score.detach().cpu().numpy())
    
    def _objective_function(self, 
                           params: Dict[str, Any], 
                           indicators: np.ndarray, 
                           price_changes: np.ndarray) -> Dict[str, Any]:
        """Objective function for Hyperopt."""
        try:
            score = self._evaluate_strategy_gpu(indicators, price_changes, params)
            
            self.logger.debug(f"Params: {params}, Score: {score}")
            
            return {
                'loss': -score,  # Minimize negative score = maximize score
                'status': STATUS_OK,
                'params': params
            }
        except Exception as e:
            self.logger.error(f"Error in objective function: {e}")
            return {
                'loss': float('inf'),
                'status': 'error'
            }
    
    def optimize(self, 
                strategy_name: str, 
                symbol: str,
                indicators: np.ndarray, 
                price_changes: np.ndarray,
                param_space: Dict[str, Any],
                max_evals: int = 100) -> Dict[str, Any]:
        """Run Hyperopt optimization for a strategy."""
        self.logger.info(f"Starting optimization for {strategy_name} on {symbol}")
        
        # Set up Hyperopt
        trials = Trials()
        
        # Define objective with data
        def objective(params):
            return self._objective_function(params, indicators, price_changes)
        
        try:
            best = fmin(
                fn=objective,
                space=param_space,
                algo=tpe.suggest,
                max_evals=max_evals,
                trials=trials
            )
            
            # Save results
            results = {
                'best_params': best,
                'trials': len(trials),
                'best_loss': trials.best_trial['result']['loss']
            }
            
            results_path = self.results_dir / f"{strategy_name}_{symbol}_results.json"
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=4)
            
            self.logger.info(f"Optimization completed. Best params: {best}")
            return results
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            return {'error': str(e)}
    
    def load_cached_results(self, strategy_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Load cached optimization results."""
        cache_path = self.results_dir / f"{strategy_name}_{symbol}_results.json"
        
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                return json.load(f)
        return None
    
    def cache_parameters(self, strategy_name: str, symbol: str, 
                        params: Dict[str, Any]) -> None:
        """Cache optimized parameters."""
        cache_path = self.cache_dir / f"{strategy_name}_{symbol}_params.json"
        with open(cache_path, 'w') as f:
            json.dump(params, f, indent=4)


class ParameterSpace:
    """Strategy-agnostic parameter space following hexagonal architecture."""

    def __init__(self):
        from infrastructure.optimization.hyperopt_space import parameter_space
        self._param_space = parameter_space

    def get_space(self, strategy_name: str):
        """Get parameter space for a given strategy via the strategy registry."""
        return self._param_space.get_space(strategy_name)
"""
Experiment Tracking System - For reproducible research and institutional compliance
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os
import subprocess
from pathlib import Path


class ExperimentTracker:
    """
    System for tracking experiments with reproducible run IDs based on:
    - Configuration
    - Strategies
    - Symbols
    - Date range
    - Git commit hash
    """
    
    def __init__(self, results_base_path: str = "./data/results"):
        self.results_base_path = Path(results_base_path)
        self.results_base_path.mkdir(parents=True, exist_ok=True)
        
        # Get git commit hash for reproducibility
        try:
            self.git_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
        except:
            self.git_commit_hash = "unknown"
    
    def generate_run_id(self, config: Dict[str, Any], 
                       strategies: list, 
                       symbols: list, 
                       date_range: tuple,
                       custom_suffix: str = "") -> str:
        """
        Generate a unique run ID based on configuration parameters.
        
        Args:
            config: Configuration dictionary
            strategies: List of strategy names
            symbols: List of symbols
            date_range: Tuple of (start_date, end_date)
            custom_suffix: Optional custom suffix for the run ID
            
        Returns:
            Unique run ID string
        """
        # Create a hashable representation of the inputs
        hash_input = {
            'config': config,
            'strategies': sorted(strategies),  # Sort for consistency
            'symbols': sorted(symbols),        # Sort for consistency
            'date_range': date_range,
            'git_commit': self.git_commit_hash
        }
        
        # Convert to JSON string for consistent hashing
        json_string = json.dumps(hash_input, sort_keys=True, default=str)
        
        # Generate SHA256 hash
        run_hash = hashlib.sha256(json_string.encode()).hexdigest()[:16]  # Use first 16 chars
        
        # Create run ID with timestamp for readability
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{timestamp}_{run_hash}"
        
        if custom_suffix:
            run_id += f"_{custom_suffix}"
        
        return run_id
    
    def save_experiment_results(self, run_id: str, results: Dict[str, Any]) -> str:
        """
        Save experiment results to a file named by the run ID.
        
        Args:
            run_id: Unique run identifier
            results: Results dictionary to save
            
        Returns:
            Path to saved results file
        """
        results_file = self.results_base_path / f"{run_id}.json"
        
        # Add metadata to results
        enriched_results = {
            'run_id': run_id,
            'timestamp': datetime.now().isoformat(),
            'git_commit': self.git_commit_hash,
            'results': results
        }
        
        with open(results_file, 'w') as f:
            json.dump(enriched_results, f, indent=2, default=str)
        
        return str(results_file)
    
    def load_experiment_results(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load experiment results by run ID.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Results dictionary or None if not found
        """
        results_file = self.results_base_path / f"{run_id}.json"
        
        if not results_file.exists():
            return None
        
        with open(results_file, 'r') as f:
            return json.load(f)
    
    def list_experiments(self) -> list:
        """
        List all available experiment run IDs.
        
        Returns:
            List of run ID strings
        """
        experiment_files = list(self.results_base_path.glob("run_*.json"))
        run_ids = []
        
        for file_path in experiment_files:
            run_id = file_path.stem  # Remove .json extension
            run_ids.append(run_id)
        
        return sorted(run_ids)
    
    def get_experiment_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific experiment without loading full results.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Metadata dictionary or None if not found
        """
        results = self.load_experiment_results(run_id)
        if results is None:
            return None
        
        # Return only metadata, not full results
        return {
            'run_id': results.get('run_id'),
            'timestamp': results.get('timestamp'),
            'git_commit': results.get('git_commit'),
            'has_results': 'results' in results
        }


# Global experiment tracker instance
experiment_tracker = ExperimentTracker()


def get_experiment_tracker() -> ExperimentTracker:
    """Get the global experiment tracker instance."""
    return experiment_tracker


def generate_run_id(config: Dict[str, Any], 
                   strategies: list, 
                   symbols: list, 
                   date_range: tuple,
                   custom_suffix: str = "") -> str:
    """Convenience function to generate a run ID."""
    tracker = get_experiment_tracker()
    return tracker.generate_run_id(config, strategies, symbols, date_range, custom_suffix)


def save_experiment_results(run_id: str, results: Dict[str, Any]) -> str:
    """Convenience function to save experiment results."""
    tracker = get_experiment_tracker()
    return tracker.save_experiment_results(run_id, results)


def load_experiment_results(run_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function to load experiment results."""
    tracker = get_experiment_tracker()
    return tracker.load_experiment_results(run_id)
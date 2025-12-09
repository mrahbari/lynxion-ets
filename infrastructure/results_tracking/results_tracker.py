"""Comprehensive system for tracking all results: hyperopt, backtests, parameters, etc."""

import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from pathlib import Path
import pickle

from shared.logger import EnhancedLogger


class ResultsTracker:
    """
    Comprehensive system for tracking all optimization and backtest results.
    Stores hyperopt results, backtest results, parameters, performance metrics, and timestamps.
    Supports both JSON file storage and SQLite database.
    """
    
    def __init__(self, 
                 storage_dir: str = "data/results_storage",
                 use_database: bool = True,
                 db_path: str = "data/results.db"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.use_database = use_database
        self.db_path = Path(db_path)
        self.logger = EnhancedLogger("ResultsTracker")
        
        if use_database:
            self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables and indexes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table for hyperopt results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hyperopt_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                parameters TEXT NOT NULL,
                best_value REAL,
                trials_completed INTEGER,
                optimization_objective TEXT,
                execution_time REAL,
                notes TEXT
            )
        ''')

        # Table for backtest results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                parameters TEXT NOT NULL,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                total_trades INTEGER,
                profit_factor REAL,
                execution_time REAL,
                notes TEXT
            )
        ''')

        # Table for combined runs (hyperopt + backtest workflow)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS combined_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                hyperopt_result_id INTEGER,
                backtest_result_id INTEGER,
                workflow_type TEXT,
                final_score REAL,
                notes TEXT,
                FOREIGN KEY (hyperopt_result_id) REFERENCES hyperopt_results (id),
                FOREIGN KEY (backtest_result_id) REFERENCES backtest_results (id)
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hyperopt_strategy_symbol ON hyperopt_results (strategy_name, symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hyperopt_timestamp ON hyperopt_results (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backtest_strategy_symbol ON backtest_results (strategy_name, symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backtest_timestamp ON backtest_results (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_combined_strategy_symbol ON combined_runs (strategy_name, symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_combined_timestamp ON combined_runs (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_combined_run_id ON combined_runs (run_id)')

        conn.commit()
        conn.close()
    
    def save_hyperopt_result(self, 
                           strategy_name: str,
                           symbol: str, 
                           parameters: Dict[str, Any],
                           best_value: float,
                           trials_completed: int,
                           optimization_objective: str = None,
                           execution_time: float = None,
                           notes: str = None) -> int:
        """Save hyperopt optimization result."""
        if self.use_database:
            return self._save_hyperopt_result_db(
                strategy_name, symbol, parameters, best_value,
                trials_completed, optimization_objective, execution_time, notes
            )
        else:
            return self._save_hyperopt_result_file(
                strategy_name, symbol, parameters, best_value,
                trials_completed, optimization_objective, execution_time, notes
            )
    
    def _save_hyperopt_result_db(self,
                               strategy_name: str,
                               symbol: str,
                               parameters: Dict[str, Any],
                               best_value: float,
                               trials_completed: int,
                               optimization_objective: str = None,
                               execution_time: float = None,
                               notes: str = None) -> int:
        """Save hyperopt result to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO hyperopt_results 
            (strategy_name, symbol, parameters, best_value, trials_completed, 
             optimization_objective, execution_time, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name, symbol, json.dumps(parameters), best_value,
            trials_completed, optimization_objective, execution_time, notes
        ))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.logger.info(f"Saved hyperopt result to DB with ID {result_id}")
        return result_id
    
    def _save_hyperopt_result_file(self,
                                 strategy_name: str,
                                 symbol: str,
                                 parameters: Dict[str, Any],
                                 best_value: float,
                                 trials_completed: int,
                                 optimization_objective: str = None,
                                 execution_time: float = None,
                                 notes: str = None) -> int:
        """Save hyperopt result to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        # Sanitize symbol name to avoid file system issues
        sanitized_symbol = symbol.replace('/', '_').replace(':', '_')
        filename = f"hyperopt_{strategy_name}_{sanitized_symbol}_{timestamp}.json"
        filepath = self.storage_dir / filename

        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "parameters": parameters,
            "best_value": best_value,
            "trials_completed": trials_completed,
            "optimization_objective": optimization_objective,
            "execution_time": execution_time,
            "notes": notes
        }

        with open(filepath, 'w') as f:
            json.dump(result, f, indent=4, default=str)

        self.logger.info(f"Saved hyperopt result to file: {filepath}")
        return hash(str(result))  # Return a hash as ID for file-based storage
    
    def save_backtest_result(self,
                           strategy_name: str,
                           symbol: str,
                           parameters: Dict[str, Any],
                           total_return: float,
                           sharpe_ratio: float,
                           max_drawdown: float,
                           win_rate: float,
                           total_trades: int,
                           profit_factor: float,
                           execution_time: float = None,
                           notes: str = None) -> int:
        """Save backtest result."""
        if self.use_database:
            return self._save_backtest_result_db(
                strategy_name, symbol, parameters, total_return, sharpe_ratio,
                max_drawdown, win_rate, total_trades, profit_factor,
                execution_time, notes
            )
        else:
            return self._save_backtest_result_file(
                strategy_name, symbol, parameters, total_return, sharpe_ratio,
                max_drawdown, win_rate, total_trades, profit_factor,
                execution_time, notes
            )
    
    def _save_backtest_result_db(self,
                               strategy_name: str,
                               symbol: str,
                               parameters: Dict[str, Any],
                               total_return: float,
                               sharpe_ratio: float,
                               max_drawdown: float,
                               win_rate: float,
                               total_trades: int,
                               profit_factor: float,
                               execution_time: float = None,
                               notes: str = None) -> int:
        """Save backtest result to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO backtest_results
            (strategy_name, symbol, parameters, total_return, sharpe_ratio,
             max_drawdown, win_rate, total_trades, profit_factor, execution_time, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name, symbol, json.dumps(parameters), total_return,
            sharpe_ratio, max_drawdown, win_rate, total_trades, profit_factor,
            execution_time, notes
        ))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.logger.info(f"Saved backtest result to DB with ID {result_id}")
        return result_id
    
    def _save_backtest_result_file(self,
                                 strategy_name: str,
                                 symbol: str,
                                 parameters: Dict[str, Any],
                                 total_return: float,
                                 sharpe_ratio: float,
                                 max_drawdown: float,
                                 win_rate: float,
                                 total_trades: int,
                                 profit_factor: float,
                                 execution_time: float = None,
                                 notes: str = None) -> int:
        """Save backtest result to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"backtest_{strategy_name}_{symbol}_{timestamp}.json"
        filepath = self.storage_dir / filename
        
        result = {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "parameters": parameters,
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "profit_factor": profit_factor,
            "execution_time": execution_time,
            "notes": notes
        }
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=4, default=str)
        
        self.logger.info(f"Saved backtest result to file: {filepath}")
        return hash(str(result))  # Return a hash as ID for file-based storage
    
    def link_hyperopt_and_backtest(self,
                                  run_id: str,
                                  strategy_name: str,
                                  symbol: str,
                                  hyperopt_result_id: int,
                                  backtest_result_id: int,
                                  workflow_type: str = "hyperopt_then_backtest",
                                  final_score: float = None,
                                  notes: str = None) -> int:
        """Link a hyperopt result with a backtest result (for workflow tracking)."""
        if self.use_database:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO combined_runs
                (run_id, strategy_name, symbol, hyperopt_result_id, backtest_result_id,
                 workflow_type, final_score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_id, strategy_name, symbol, hyperopt_result_id,
                backtest_result_id, workflow_type, final_score, notes
            ))
            
            result_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"Linked hyperopt and backtest results with run ID {run_id}")
            return result_id
        else:
            # For file-based storage, create a link file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"link_{run_id}_{timestamp}.json"
            filepath = self.storage_dir / filename
            
            link_data = {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "strategy_name": strategy_name,
                "symbol": symbol,
                "hyperopt_result_id": hyperopt_result_id,
                "backtest_result_id": backtest_result_id,
                "workflow_type": workflow_type,
                "final_score": final_score,
                "notes": notes
            }
            
            with open(filepath, 'w') as f:
                json.dump(link_data, f, indent=4, default=str)
            
            self.logger.info(f"Created link file: {filepath}")
            return hash(str(link_data))
    
    def get_hyperopt_results(self,
                           strategy_name: str = None,
                           symbol: str = None,
                           limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve hyperopt results with optional filters."""
        if self.use_database:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM hyperopt_results WHERE 1=1"
            params = []
            
            if strategy_name:
                query += " AND strategy_name = ?"
                params.append(strategy_name)
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            results = []
            for row in rows:
                result_dict = dict(zip(columns, row))
                # Parse JSON parameters
                result_dict['parameters'] = json.loads(result_dict['parameters'])
                results.append(result_dict)
            
            conn.close()
            return results
        else:
            # For file-based storage, read all hyperopt result files
            results = []
            for file_path in self.storage_dir.glob("hyperopt_*.json"):
                try:
                    with open(file_path, 'r') as f:
                        result = json.load(f)
                        if strategy_name and result['strategy_name'] != strategy_name:
                            continue
                        if symbol and result['symbol'] != symbol:
                            continue
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error reading hyperopt result file {file_path}: {e}")
            
            # Sort by timestamp in descending order
            results.sort(key=lambda x: x['timestamp'], reverse=True)
            
            if limit:
                results = results[:limit]
            
            return results
    
    def get_backtest_results(self,
                           strategy_name: str = None,
                           symbol: str = None,
                           limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve backtest results with optional filters."""
        if self.use_database:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM backtest_results WHERE 1=1"
            params = []
            
            if strategy_name:
                query += " AND strategy_name = ?"
                params.append(strategy_name)
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            results = []
            for row in rows:
                result_dict = dict(zip(columns, row))
                # Parse JSON parameters
                result_dict['parameters'] = json.loads(result_dict['parameters'])
                results.append(result_dict)
            
            conn.close()
            return results
        else:
            # For file-based storage, read all backtest result files
            results = []
            for file_path in self.storage_dir.glob("backtest_*.json"):
                try:
                    with open(file_path, 'r') as f:
                        result = json.load(f)
                        if strategy_name and result['strategy_name'] != strategy_name:
                            continue
                        if symbol and result['symbol'] != symbol:
                            continue
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error reading backtest result file {file_path}: {e}")
            
            # Sort by timestamp in descending order
            results.sort(key=lambda x: x['timestamp'], reverse=True)
            
            if limit:
                results = results[:limit]
            
            return results
    
    def get_best_parameters(self, 
                          strategy_name: str, 
                          symbol: str, 
                          metric: str = "sharpe_ratio") -> Optional[Dict[str, Any]]:
        """Get the best parameters based on a specific metric."""
        if metric in ["sharpe_ratio", "total_return", "profit_factor"]:
            # Look for backtest results
            results = self.get_backtest_results(strategy_name, symbol, limit=50)
            if not results:
                return None
            
            # Find the best result based on the metric
            best_result = max(results, key=lambda x: x.get(metric, float('-inf')))
            return {
                'parameters': best_result['parameters'],
                'result': best_result,
                'metric_value': best_result.get(metric)
            }
        else:  # For hyperopt results
            results = self.get_hyperopt_results(strategy_name, symbol, limit=50)
            if not results:
                return None
            
            # For hyperopt, lower is better (it minimizes the objective)
            best_result = min(results, key=lambda x: x.get('best_value', float('inf')))
            return {
                'parameters': best_result['parameters'],
                'result': best_result,
                'metric_value': -best_result['best_value']  # Convert to positive for reporting
            }
    
    def export_results_summary(self, filepath: str) -> bool:
        """Export a summary of all results to a file."""
        try:
            # Get all results
            hyperopt_results = self.get_hyperopt_results()
            backtest_results = self.get_backtest_results()

            summary = {
                "summary": {
                    "total_hyperopt_runs": len(hyperopt_results),
                    "total_backtest_runs": len(backtest_results),
                    "timestamp": datetime.now().isoformat()
                },
                "hyperopt_results": hyperopt_results[:100],  # Limit to first 100 for summary
                "backtest_results": backtest_results[:100]   # Limit to first 100 for summary
            }

            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, default=str)

            self.logger.info(f"Exported results summary to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting results summary: {e}")
            return False

    def cleanup_old_results(self,
                          days_to_keep: int = 90,
                          strategy_name: str = None,
                          symbol: str = None) -> Dict[str, int]:
        """Remove old results to manage database size."""
        if not self.use_database:
            return {"error": "Database not in use"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        # Build SQL conditions
        conditions = ["timestamp < ?"]
        params = [cutoff_date]

        if strategy_name:
            conditions.append("strategy_name = ?")
            params.append(strategy_name)

        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)

        where_clause = " AND ".join(conditions)

        # Delete old hyperopt results
        cursor.execute(f"DELETE FROM hyperopt_results WHERE {where_clause}", params)
        hyperopt_deleted = cursor.rowcount

        # Delete old backtest results
        cursor.execute(f"DELETE FROM backtest_results WHERE {where_clause}", params)
        backtest_deleted = cursor.rowcount

        # Delete old combined runs that reference deleted results
        cursor.execute("""
            DELETE FROM combined_runs
            WHERE hyperopt_result_id IN (
                SELECT id FROM hyperopt_results WHERE {0}
            ) OR backtest_result_id IN (
                SELECT id FROM backtest_results WHERE {0}
            )
        """.format(where_clause), params)
        combined_deleted = cursor.rowcount

        conn.commit()
        conn.close()

        result = {
            "hyperopt_deleted": hyperopt_deleted,
            "backtest_deleted": backtest_deleted,
            "combined_deleted": combined_deleted,
            "total_deleted": hyperopt_deleted + backtest_deleted + combined_deleted
        }

        self.logger.info(f"Cleaned up old results: {result}")
        return result

    def get_database_size(self) -> Dict[str, Any]:
        """Get database size and statistics."""
        if not self.use_database or not self.db_path.exists():
            return {"error": "Database file not found"}

        size_bytes = self.db_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        # Get row counts
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM hyperopt_results")
        hyperopt_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM backtest_results")
        backtest_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM combined_runs")
        combined_count = cursor.fetchone()[0]

        conn.close()

        return {
            "size_mb": size_mb,
            "size_bytes": size_bytes,
            "hyperopt_results": hyperopt_count,
            "backtest_results": backtest_count,
            "combined_runs": combined_count,
            "total_records": hyperopt_count + backtest_count + combined_count
        }


class ResultsAnalyzer:
    """Analyzer for results data to provide insights and recommendations."""
    
    def __init__(self, results_tracker: ResultsTracker):
        self.tracker = results_tracker
        self.logger = EnhancedLogger("ResultsAnalyzer")
    
    def analyze_strategy_performance(self, strategy_name: str) -> Dict[str, Any]:
        """Analyze performance of a specific strategy across all symbols."""
        backtest_results = self.tracker.get_backtest_results(strategy_name=strategy_name)
        
        if not backtest_results:
            return {"error": f"No backtest results found for strategy {strategy_name}"}
        
        # Calculate aggregate metrics
        total_returns = [r['total_return'] for r in backtest_results if 'total_return' in r]
        sharpe_ratios = [r['sharpe_ratio'] for r in backtest_results if 'sharpe_ratio' in r]
        win_rates = [r['win_rate'] for r in backtest_results if 'win_rate' in r]
        
        analysis = {
            "strategy": strategy_name,
            "total_runs": len(backtest_results),
            "avg_total_return": sum(total_returns) / len(total_returns) if total_returns else 0,
            "avg_sharpe_ratio": sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0,
            "avg_win_rate": sum(win_rates) / len(win_rates) if win_rates else 0,
            "best_total_return": max(total_returns) if total_returns else 0,
            "best_sharpe_ratio": max(sharpe_ratios) if sharpe_ratios else 0,
            "symbols_tested": list(set(r['symbol'] for r in backtest_results)),
            "metrics_range": {
                "total_return": {"min": min(total_returns) if total_returns else 0, "max": max(total_returns) if total_returns else 0},
                "sharpe_ratio": {"min": min(sharpe_ratios) if sharpe_ratios else 0, "max": max(sharpe_ratios) if sharpe_ratios else 0},
            }
        }
        
        return analysis
    
    def find_best_configurations(self, strategy_name: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Find the top N best configurations for a strategy."""
        backtest_results = self.tracker.get_backtest_results(strategy_name=strategy_name)
        
        if not backtest_results:
            return []
        
        # Sort by sharpe ratio (primary) and total return (secondary)
        sorted_results = sorted(
            backtest_results,
            key=lambda x: (x.get('sharpe_ratio', 0), x.get('total_return', 0)),
            reverse=True
        )
        
        return sorted_results[:top_n]
    
    def detect_overfitting_signs(self, strategy_name: str) -> List[Dict[str, Any]]:
        """Detect potential overfitting in optimization results."""
        # Look for results with very high returns but low out-of-sample performance
        # This is a basic implementation - in practice you'd want cross-validation
        
        backtest_results = self.tracker.get_backtest_results(strategy_name=strategy_name)
        hyperopt_results = self.tracker.get_hyperopt_results(strategy_name=strategy_name)
        
        potential_overfit = []
        
        for backtest in backtest_results:
            # Look for very high returns that might indicate overfitting
            if backtest.get('total_return', 0) > 5:  # 500% return might be suspicious
                potential_overfit.append({
                    "type": "high_return_warning",
                    "symbol": backtest['symbol'],
                    "return": backtest['total_return'],
                    "sharpe": backtest.get('sharpe_ratio', 0),
                    "trades": backtest.get('total_trades', 0),
                    "parameters": backtest['parameters']
                })
        
        return potential_overfit
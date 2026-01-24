"""
Shadow Deployment KPI Dashboard - Track key metrics for shadow deployment
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
from pathlib import Path

from shared.logger import EnhancedLogger


class ShadowKPIMonitor:
    """
    System for monitoring and tracking Shadow Deployment KPIs.
    Tracks metrics like signal deviation vs backtest, win rate deviation, etc.
    """
    
    def __init__(self, base_path: str = "./data/shadow_monitoring"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = EnhancedLogger("ShadowKPIMonitor")
        
        # Initialize tracking files
        self.kpi_log_file = self.base_path / "shadow_kpi_log.json"
        self.alerts_file = self.base_path / "shadow_alerts.json"
        
        # Initialize data structures
        self.kpi_history = self._load_kpi_history()
        self.alerts_history = self._load_alerts_history()
    
    def _load_kpi_history(self) -> List[Dict[str, Any]]:
        """Load historical KPI data."""
        if self.kpi_log_file.exists():
            with open(self.kpi_log_file, 'r') as f:
                return json.load(f)
        return []
    
    def _load_alerts_history(self) -> List[Dict[str, Any]]:
        """Load historical alerts data."""
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                return json.load(f)
        return []
    
    def calculate_kpis(self, 
                      current_metrics: Dict[str, Any], 
                      baseline_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate shadow deployment KPIs based on current vs baseline metrics.
        
        Args:
            current_metrics: Current shadow deployment metrics
            baseline_metrics: Baseline backtest metrics
            
        Returns:
            Dictionary with calculated KPIs
        """
        kpis = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        # Calculate signal deviation vs backtest (< 15% threshold)
        baseline_signals = baseline_metrics.get('total_signals', 0)
        current_signals = current_metrics.get('total_signals', 0)
        signal_deviation = abs(current_signals - baseline_signals) / baseline_signals if baseline_signals > 0 else 0
        kpis['metrics']['signal_deviation_vs_backtest'] = {
            'value': signal_deviation,
            'threshold': 0.15,
            'alert': signal_deviation > 0.15,
            'baseline': baseline_signals,
            'current': current_signals
        }
        
        # Calculate win rate deviation (< 10% threshold)
        baseline_win_rate = baseline_metrics.get('win_rate', 0)
        current_win_rate = current_metrics.get('win_rate', 0)
        win_rate_deviation = abs(current_win_rate - baseline_win_rate) / abs(baseline_win_rate) if baseline_win_rate != 0 else 0
        kpis['metrics']['win_rate_deviation'] = {
            'value': win_rate_deviation,
            'threshold': 0.10,
            'alert': win_rate_deviation > 0.10,
            'baseline': baseline_win_rate,
            'current': current_win_rate
        }
        
        # Calculate avg trade PnL deviation (< 15% threshold)
        baseline_avg_pnl = baseline_metrics.get('avg_trade_pnl', 0)
        current_avg_pnl = current_metrics.get('avg_trade_pnl', 0)
        avg_pnl_deviation = abs(current_avg_pnl - baseline_avg_pnl) / abs(baseline_avg_pnl) if baseline_avg_pnl != 0 else 0
        kpis['metrics']['avg_trade_pnl_deviation'] = {
            'value': avg_pnl_deviation,
            'threshold': 0.15,
            'alert': avg_pnl_deviation > 0.15,
            'baseline': baseline_avg_pnl,
            'current': current_avg_pnl
        }
        
        # Calculate trade count deviation (< 20% threshold)
        baseline_trade_count = baseline_metrics.get('total_trades', 0)
        current_trade_count = current_metrics.get('total_trades', 0)
        trade_count_deviation = abs(current_trade_count - baseline_trade_count) / baseline_trade_count if baseline_trade_count > 0 else 0
        kpis['metrics']['trade_count_deviation'] = {
            'value': trade_count_deviation,
            'threshold': 0.20,
            'alert': trade_count_deviation > 0.20,
            'baseline': baseline_trade_count,
            'current': current_trade_count
        }
        
        # Calculate regime classification drift (< 10% threshold)
        baseline_regime_accuracy = baseline_metrics.get('regime_classification_accuracy', 1.0)
        current_regime_accuracy = current_metrics.get('regime_classification_accuracy', 1.0)
        regime_drift = abs(baseline_regime_accuracy - current_regime_accuracy)
        kpis['metrics']['regime_classification_drift'] = {
            'value': regime_drift,
            'threshold': 0.10,
            'alert': regime_drift > 0.10,
            'baseline': baseline_regime_accuracy,
            'current': current_regime_accuracy
        }
        
        # Calculate overall KPI score (0-1 scale, higher is better)
        alert_count = sum(1 for metric in kpis['metrics'].values() if metric['alert'])
        total_metrics = len(kpis['metrics'])
        kpis['overall_kpi_score'] = (total_metrics - alert_count) / total_metrics if total_metrics > 0 else 1.0
        
        return kpis
    
    def check_alerts(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for alerts based on KPI thresholds."""
        alerts = []
        
        for metric_name, metric_data in kpis['metrics'].items():
            if metric_data['alert']:
                alert = {
                    'timestamp': kpis['timestamp'],
                    'metric': metric_name,
                    'current_value': metric_data['value'],
                    'threshold': metric_data['threshold'],
                    'baseline_value': metric_data.get('baseline', 'N/A'),
                    'current_metric_value': metric_data.get('current', 'N/A'),
                    'severity': 'HIGH' if metric_data['value'] > metric_data['threshold'] * 2 else 'MEDIUM'
                }
                alerts.append(alert)
        
        return alerts
    
    def log_kpis(self, kpis: Dict[str, Any]):
        """Log KPIs to history."""
        self.kpi_history.append(kpis)
        
        # Keep only last 30 days of data
        cutoff_date = datetime.now() - timedelta(days=30)
        self.kpi_history = [
            k for k in self.kpi_history 
            if datetime.fromisoformat(k['timestamp']) >= cutoff_date
        ]
        
        # Save to file
        with open(self.kpi_log_file, 'w') as f:
            json.dump(self.kpi_history, f, indent=2, default=str)
    
    def log_alerts(self, alerts: List[Dict[str, Any]]):
        """Log alerts to history."""
        self.alerts_history.extend(alerts)
        
        # Keep only last 30 days of data
        cutoff_date = datetime.now() - timedelta(days=30)
        self.alerts_history = [
            a for a in self.alerts_history 
            if datetime.fromisoformat(a['timestamp']) >= cutoff_date
        ]
        
        # Save to file
        with open(self.alerts_file, 'w') as f:
            json.dump(self.alerts_history, f, indent=2, default=str)
    
    def generate_dashboard_report(self) -> Dict[str, Any]:
        """Generate a comprehensive dashboard report."""
        if not self.kpi_history:
            return {'error': 'No KPI data available'}
        
        # Calculate recent trends (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_kpis = [
            k for k in self.kpi_history 
            if datetime.fromisoformat(k['timestamp']) >= week_ago
        ]
        
        # Calculate averages and trends
        avg_kpi_score = np.mean([k['overall_kpi_score'] for k in recent_kpis]) if recent_kpis else 0
        
        # Calculate metric-specific averages
        metric_averages = {}
        for metric_name in self.kpi_history[0]['metrics'].keys():
            values = [k['metrics'][metric_name]['value'] for k in recent_kpis if metric_name in k['metrics']]
            if values:
                metric_averages[metric_name] = {
                    'avg': float(np.mean(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'std': float(np.std(values))
                }
        
        # Get recent alerts
        recent_alerts = [
            a for a in self.alerts_history 
            if datetime.fromisoformat(a['timestamp']) >= week_ago
        ]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_kpi_records': len(self.kpi_history),
                'recent_kpi_records': len(recent_kpis),
                'total_alerts': len(self.alerts_history),
                'recent_alerts': len(recent_alerts),
                'avg_kpi_score_7d': float(avg_kpi_score),
                'latest_kpi_score': self.kpi_history[-1]['overall_kpi_score'] if self.kpi_history else 0
            },
            'metric_averages_7d': metric_averages,
            'recent_alerts': recent_alerts[-10:],  # Last 10 alerts
            'kpi_trend': self._calculate_kpi_trend(recent_kpis),
            'recommendations': self._generate_recommendations(metric_averages, recent_alerts)
        }
        
        return report
    
    def _calculate_kpi_trend(self, recent_kpis: List[Dict[str, Any]]) -> str:
        """Calculate overall KPI trend."""
        if len(recent_kpis) < 2:
            return 'INSUFFICIENT_DATA'
        
        scores = [k['overall_kpi_score'] for k in recent_kpis]
        if len(scores) < 2:
            return 'INSUFFICIENT_DATA'
        
        # Simple linear regression slope
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        
        if slope > 0.01:
            return 'IMPROVING'
        elif slope < -0.01:
            return 'DECLINING'
        else:
            return 'STABLE'
    
    def _generate_recommendations(self, metric_averages: Dict[str, Any], recent_alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on KPIs and alerts."""
        recommendations = []
        
        # Check if any metrics are consistently exceeding thresholds
        high_deviation_metrics = []
        for metric_name, avg_data in metric_averages.items():
            if avg_data['avg'] > 0.15:  # High deviation
                high_deviation_metrics.append(metric_name)
        
        if high_deviation_metrics:
            recommendations.append(f"High deviation detected in: {', '.join(high_deviation_metrics)}. Investigate potential causes.")
        
        # Check alert frequency
        if len(recent_alerts) > 10:  # More than 10 alerts recently
            recommendations.append("High alert frequency detected. Consider system review.")
        elif len(recent_alerts) == 0:
            recommendations.append("No alerts in recent period - system appears stable.")
        
        # Check overall KPI score
        if metric_averages and 'signal_deviation_vs_backtest' in metric_averages:
            signal_dev_avg = metric_averages['signal_deviation_vs_backtest']['avg']
            if signal_dev_avg > 0.20:  # Much higher than threshold
                recommendations.append("Signal deviation significantly higher than threshold. Model drift may be occurring.")
        
        if not recommendations:
            recommendations.append("System performing within expected parameters.")
        
        return recommendations


def generate_shadow_kpi_report(current_metrics: Dict[str, Any], 
                              baseline_metrics: Dict[str, Any],
                              base_path: str = "./data/shadow_monitoring") -> Dict[str, Any]:
    """
    Convenience function to generate shadow KPI report.
    
    Args:
        current_metrics: Current shadow deployment metrics
        baseline_metrics: Baseline backtest metrics
        base_path: Base path for storing monitoring data
        
    Returns:
        Dictionary with KPI report
    """
    monitor = ShadowKPIMonitor(base_path=base_path)
    
    # Calculate KPIs
    kpis = monitor.calculate_kpis(current_metrics, baseline_metrics)
    
    # Log KPIs
    monitor.log_kpis(kpis)
    
    # Check for alerts
    alerts = monitor.check_alerts(kpis)
    
    # Log alerts if any
    if alerts:
        monitor.log_alerts(alerts)
    
    # Generate dashboard report
    report = monitor.generate_dashboard_report()
    
    return report
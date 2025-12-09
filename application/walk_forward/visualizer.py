"""Visualization components for Walk-Forward Optimization results."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path


class WFVisualizer:
    """Visualizer for Walk-Forward Optimization results."""
    
    def __init__(self, output_dir: str = "./results/wfo/plots"):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set style for matplotlib
        plt.style.use('default')
    
    def plot_equity_curve(self, 
                         results: Dict[str, Any], 
                         symbol: str = None, 
                         save_path: str = None) -> go.Figure:
        """
        Plot equity curve for Walk-Forward results.
        
        Args:
            results: WFO results dictionary
            symbol: Specific symbol to plot (if multi-asset)
            save_path: Path to save the plot (optional)
        """
        if symbol:
            # For a specific symbol
            symbol_results = results.get('multi_asset_results', {}).get(symbol, {})
            out_of_sample_results = symbol_results.get('out_of_sample_results', [])
        else:
            # For overall results
            out_of_sample_results = results.get('out_of_sample_results', [])
        
        # Extract equity curves from results
        all_equity_data = []
        timestamps = []
        
        for i, period_result in enumerate(out_of_sample_results):
            equity_curve = period_result.get('equity_curve', [])
            if equity_curve and isinstance(equity_curve, list):
                # Extract equity values and timestamps
                for point in equity_curve:
                    if isinstance(point, dict):
                        all_equity_data.append(point.get('equity', 0))
                        timestamps.append(point.get('timestamp', f'Period_{i}'))
                    else:
                        # If equity_curve is just values, create synthetic timestamps
                        all_equity_data.extend(equity_curve)
                        timestamps.extend([f'Point_{j}_Period_{i}' for j in range(len(equity_curve))])
        
        if not all_equity_data:
            # If no detailed equity curves, create a simple cumulative return visualization
            cumulative_returns = []
            current_value = 1000  # Starting value
            
            for i, period_result in enumerate(out_of_sample_results):
                return_pct = period_result.get('total_return', 0)
                if cumulative_returns:
                    current_value = cumulative_returns[-1] * (1 + return_pct)
                else:
                    current_value = 1000 * (1 + return_pct)
                cumulative_returns.append(current_value)
            
            timestamps = list(range(len(cumulative_returns)))
            all_equity_data = cumulative_returns
        
        # Create plotly figure
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=all_equity_data,
            mode='lines+markers',
            name=f'{symbol} Equity Curve' if symbol else 'Aggregate Equity Curve',
            line=dict(width=2),
            marker=dict(size=4)
        ))
        
        fig.update_layout(
            title=f'Walk-Forward Equity Curve - {symbol}' if symbol else 'Walk-Forward Aggregate Equity Curve',
            xaxis_title='Time',
            yaxis_title='Equity ($)',
            hovermode='x unified',
            template='plotly_white'
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    def plot_roi_bars(self, 
                      results: Dict[str, Any], 
                      symbol: str = None, 
                      save_path: str = None) -> go.Figure:
        """
        Plot ROI per window as bars.
        
        Args:
            results: WFO results dictionary
            symbol: Specific symbol to plot (if multi-asset)
            save_path: Path to save the plot (optional)
        """
        if symbol:
            out_of_sample_results = results.get('multi_asset_results', {}).get(symbol, {}).get('out_of_sample_results', [])
        else:
            out_of_sample_results = results.get('out_of_sample_results', [])
        
        rois = [result.get('total_return', 0) for result in out_of_sample_results]
        
        # Create bar plot
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[f'Window {i+1}' for i in range(len(rois))],
            y=rois,
            name='ROI per Window',
            marker_color=['red' if roi < 0 else 'green' for roi in rois]
        ))
        
        fig.update_layout(
            title=f'Walk-Forward ROI per Window - {symbol}' if symbol else 'Walk-Forward ROI per Window',
            xaxis_title='Window',
            yaxis_title='ROI',
            hovermode='x',
            template='plotly_white'
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    def plot_drawdown_curve(self, 
                           results: Dict[str, Any], 
                           symbol: str = None, 
                           save_path: str = None) -> go.Figure:
        """
        Plot drawdown curve for Walk-Forward results.
        
        Args:
            results: WFO results dictionary
            symbol: Specific symbol to plot (if multi-asset)
            save_path: Path to save the plot (optional)
        """
        if symbol:
            out_of_sample_results = results.get('multi_asset_results', {}).get(symbol, {}).get('out_of_sample_results', [])
        else:
            out_of_sample_results = results.get('out_of_sample_results', [])
        
        # Calculate drawdown from equity curves if available
        all_drawdown_data = []
        timestamps = []
        
        for i, period_result in enumerate(out_of_sample_results):
            equity_curve = period_result.get('equity_curve', [])
            if equity_curve and isinstance(equity_curve, list):
                # Calculate drawdown from equity values
                equity_values = [point.get('equity', 0) if isinstance(point, dict) else point for point in equity_curve]
                equity_series = pd.Series(equity_values)
                
                # Calculate drawdown
                running_max = equity_series.expanding().max()
                drawdown = (equity_series - running_max) / running_max
                drawdown = drawdown.fillna(0)  # Fill NaN values
                
                all_drawdown_data.extend(drawdown.tolist())
                # Create proper timestamps if available
                if isinstance(equity_curve[0], dict):
                    timestamps.extend([point.get('timestamp', f'Point_{j}_Period_{i}') for j, point in enumerate(equity_curve)])
                else:
                    timestamps.extend([f'Point_{j}_Period_{i}' for j in range(len(equity_curve))])
        
        if not all_drawdown_data:
            # If no detailed data, use period max drawdowns
            all_drawdown_data = [result.get('max_drawdown', 0) for result in out_of_sample_results]
            timestamps = [f'Window {i+1}' for i in range(len(all_drawdown_data))]
        
        # Create plotly figure
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=all_drawdown_data,
            mode='lines',
            name='Drawdown',
            line=dict(color='red', width=2),
            fill='tonexty',  # Fill area below the line
            fillcolor='rgba(255, 0, 0, 0.2)'  # Light red fill
        ))
        
        fig.update_layout(
            title=f'Walk-Forward Drawdown Curve - {symbol}' if symbol else 'Walk-Forward Drawdown Curve',
            xaxis_title='Time',
            yaxis_title='Drawdown',
            hovermode='x unified',
            template='plotly_white',
            shapes=[  # Add zero line
                dict(type='line', xref='paper', x0=0, x1=1, yref='y', y0=0, y1=0, 
                     line=dict(color='black', width=1, dash='dash'))
            ]
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    def plot_parameter_evolution(self, 
                                results: Dict[str, Any], 
                                save_path: str = None) -> go.Figure:
        """
        Plot how parameters evolved across WFO periods.
        
        Args:
            results: WFO results dictionary
            save_path: Path to save the plot (optional)
        """
        param_history = results.get('optimized_parameters_history', [])
        
        if not param_history:
            # If no parameter history, return an empty plot
            fig = go.Figure()
            fig.add_annotation(text="No parameter history available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            fig.update_layout(title="Parameter Evolution - No Data Available")
            return fig
        
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(param_history)
        
        # Create subplots for each parameter
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            fig = go.Figure()
            fig.add_annotation(text="No numeric parameters to plot", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            fig.update_layout(title="Parameter Evolution - No Numeric Parameters")
            return fig
        
        # Create a subplot for each numeric parameter
        n_params = len(numeric_cols)
        if n_params <= 1:
            # If only one parameter, create a simple plot
            fig = go.Figure()
            for param in numeric_cols:
                fig.add_trace(go.Scatter(
                    x=list(range(len(df))),
                    y=df[param],
                    mode='lines+markers',
                    name=param
                ))
        else:
            # Create subplots for multiple parameters
            fig = make_subplots(
                rows=n_params, cols=1,
                subplot_titles=numeric_cols,
                vertical_spacing=0.08
            )
            
            for i, param in enumerate(numeric_cols):
                fig.add_trace(
                    go.Scatter(
                        x=list(range(len(df))),
                        y=df[param],
                        mode='lines+markers',
                        name=param
                    ),
                    row=i+1, col=1
                )
            
            fig.update_layout(
                title="Parameter Evolution Across WFO Periods",
                height=300 * n_params
            )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    def plot_performance_metrics(self, 
                                results: Dict[str, Any], 
                                save_path: str = None) -> go.Figure:
        """
        Plot key performance metrics across WFO periods.
        
        Args:
            results: WFO results dictionary
            save_path: Path to save the plot (optional)
        """
        out_of_sample_results = results.get('out_of_sample_results', [])
        
        if not out_of_sample_results:
            fig = go.Figure()
            fig.add_annotation(text="No performance results available", 
                              xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False)
            fig.update_layout(title="Performance Metrics - No Data Available")
            return fig
        
        # Extract metrics
        sharpes = [result.get('sharpe_ratio', 0) for result in out_of_sample_results]
        returns = [result.get('total_return', 0) for result in out_of_sample_results]
        drawdowns = [abs(result.get('max_drawdown', 0)) for result in out_of_sample_results]
        win_rates = [result.get('win_rate', 0) for result in out_of_sample_results]
        
        periods = list(range(len(out_of_sample_results)))
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Sharpe Ratio', 'Total Return', 'Max Drawdown', 'Win Rate'),
            vertical_spacing=0.12
        )
        
        # Sharpe Ratio
        fig.add_trace(
            go.Scatter(x=periods, y=sharpes, mode='lines+markers', name='Sharpe Ratio'),
            row=1, col=1
        )
        
        # Total Return
        fig.add_trace(
            go.Scatter(x=periods, y=returns, mode='lines+markers', name='Total Return'),
            row=1, col=2
        )
        
        # Max Drawdown
        fig.add_trace(
            go.Scatter(x=periods, y=drawdowns, mode='lines+markers', name='Max Drawdown'),
            row=2, col=1
        )
        
        # Win Rate
        fig.add_trace(
            go.Scatter(x=periods, y=win_rates, mode='lines+markers', name='Win Rate'),
            row=2, col=2
        )
        
        fig.update_layout(
            title="Performance Metrics Across WFO Periods",
            height=700
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    def generate_comprehensive_report(self, 
                                    results: Dict[str, Any], 
                                    symbols: List[str], 
                                    strategy_name: str,
                                    output_dir: str = None) -> Dict[str, str]:
        """
        Generate a comprehensive visualization report with all plots.
        
        Args:
            results: WFO results dictionary
            symbols: List of symbols analyzed
            strategy_name: Name of the strategy
            output_dir: Output directory (optional, uses default if not provided)
            
        Returns:
            Dictionary mapping plot names to file paths
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_files = {}
        
        # Generate plots for each symbol (if multi-asset) and overall
        for symbol in symbols + [None]:  # Include None for aggregate
            if symbol:
                suffix = f"_{symbol}"
                name_label = symbol
            else:
                suffix = "_aggregate"
                name_label = "Aggregate"
            
            # Equity curve
            equity_path = self.output_dir / f"equity_curve_{strategy_name}{suffix}_{timestamp}.html"
            equity_fig = self.plot_equity_curve(results, symbol, str(equity_path))
            plot_files[f'equity_curve{suffix}'] = str(equity_path)
            
            # ROI bars
            roi_path = self.output_dir / f"roi_bars_{strategy_name}{suffix}_{timestamp}.html"
            roi_fig = self.plot_roi_bars(results, symbol, str(roi_path))
            plot_files[f'roi_bars{suffix}'] = str(roi_path)
            
            # Drawdown curve
            dd_path = self.output_dir / f"drawdown_curve_{strategy_name}{suffix}_{timestamp}.html"
            dd_fig = self.plot_drawdown_curve(results, symbol, str(dd_path))
            plot_files[f'drawdown_curve{suffix}'] = str(dd_path)
        
        # Parameter evolution (aggregate)
        param_path = self.output_dir / f"parameter_evolution_{strategy_name}_{timestamp}.html"
        param_fig = self.plot_parameter_evolution(results, str(param_path))
        plot_files['parameter_evolution'] = str(param_path)
        
        # Performance metrics
        perf_path = self.output_dir / f"performance_metrics_{strategy_name}_{timestamp}.html"
        perf_fig = self.plot_performance_metrics(results, str(perf_path))
        plot_files['performance_metrics'] = str(perf_path)
        
        # Create an index HTML with all plots
        index_path = self.output_dir / f"report_index_{strategy_name}_{timestamp}.html"
        
        with open(index_path, 'w') as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Walk-Forward Optimization Report - {strategy_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .section {{ margin-bottom: 40px; }}
                    .plot-container {{ margin: 10px 0; }}
                    h1, h2 {{ color: #2c3e50; }}
                    .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <h1>Walk-Forward Optimization Report</h1>
                <div class="summary">
                    <h3>Summary</h3>
                    <p><strong>Strategy:</strong> {strategy_name}</p>
                    <p><strong>Symbols:</strong> {', '.join(symbols)}</p>
                    <p><strong>Total Periods:</strong> {results.get('total_periods', 'N/A')}</p>
                    <p><strong>Avg Sharpe Ratio:</strong> {results.get('avg_sharpe_ratio', 'N/A'): .4f}</p>
                    <p><strong>Avg Return:</strong> {results.get('avg_total_return', 'N/A'): .4f}</p>
                    <p><strong>Pass Rate:</strong> {results.get('pass_rate', 'N/A'): .2%}</p>
                </div>
                
                <h2>Performance Visualization</h2>
                
                <div class="section">
                    <h3>Performance Metrics</h3>
                    <div class="plot-container">{perf_fig.to_html(include_plotlyjs='cdn', full_html=False)}</div>
                </div>
                
                <div class="section">
                    <h3>Aggregate Equity Curve</h3>
                    <div class="plot-container">{equity_fig.to_html(include_plotlyjs='cdn', full_html=False)}</div>
                </div>
                
                <div class="section">
                    <h3>ROI per Window</h3>
                    <div class="plot-container">{roi_fig.to_html(include_plotlyjs='cdn', full_html=False)}</div>
                </div>
                
                <div class="section">
                    <h3>Drawdown Curve</h3>
                    <div class="plot-container">{dd_fig.to_html(include_plotlyjs='cdn', full_html=False)}</div>
                </div>
                
                <div class="section">
                    <h3>Parameter Evolution</h3>
                    <div class="plot-container">{param_fig.to_html(include_plotlyjs='cdn', full_html=False)}</div>
                </div>
                
                {self._generate_symbol_sections(results, symbols, timestamp, strategy_name)}
                
            </body>
            </html>
            """)
        
        plot_files['report_index'] = str(index_path)
        
        return plot_files
    
    def _generate_symbol_sections(self, results, symbols, timestamp, strategy_name):
        """Helper method to generate HTML sections for each symbol."""
        sections = ""
        for symbol in symbols:
            # Check if symbol has specific results
            symbol_results = results.get('multi_asset_results', {}).get(symbol, {})
            if not symbol_results:
                continue
                
            # Generate plots for this symbol
            equity_path = self.output_dir / f"equity_curve_{strategy_name}_{symbol}_{timestamp}.html"
            roi_path = self.output_dir / f"roi_bars_{strategy_name}_{symbol}_{timestamp}.html" 
            dd_path = self.output_dir / f"drawdown_curve_{strategy_name}_{symbol}_{timestamp}.html"
            
            sections += f"""
            <div class="section">
                <h3>{symbol} Specific Results</h3>
                
                <div class="plot-container">
                    <h4>{symbol} Equity Curve</h4>
                    {self.plot_equity_curve(results, symbol).to_html(include_plotlyjs='cdn', full_html=False)}
                </div>
                
                <div class="plot-container">
                    <h4>{symbol} ROI per Window</h4>
                    {self.plot_roi_bars(results, symbol).to_html(include_plotlyjs='cdn', full_html=False)}
                </div>
                
                <div class="plot-container">
                    <h4>{symbol} Drawdown Curve</h4>
                    {self.plot_drawdown_curve(results, symbol).to_html(include_plotlyjs='cdn', full_html=False)}
                </div>
            </div>
            """
        
        return sections
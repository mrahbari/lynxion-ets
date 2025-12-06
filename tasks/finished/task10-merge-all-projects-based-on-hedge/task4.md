I performed a thorough review and found the project needed improvement and finalization. For that reason I created a separate version and implemented these items. Now I need you to review this project carefully. Read the README files in:

vendor/lynx/hedge_fund/hedgefund_new_features


See how you can add those features to the project so that, besides running with high performance, the system is also robust and profitable in production.


Please review it step by step and improve my current project based on the recommended Enterprise Hedge Fund architecture.
Keep the existing architecture, conventions, and folder structure, but add the key features from the Enterprise Hedge Fund skeleton.

## Key Improvements & Fixes included in vendor/lynx/hedge_fund/hedgefund_new_features

### Logic Corrections
1. **Data Generation**: Fixed identical price data across symbols by using different random seeds
2. **Position Sizing**: Corrected unrealistic position sizes for low-priced assets (e.g., XRP, SHIB) with price-based constraints
3. **SL/TP Logic**: Enhanced to handle simultaneous stop loss and take profit scenarios with priority logic
4. **Risk Management**: Improved exposure and position size constraints to prevent excessive risk

### Performance Validation
- **P&L Differentiation**: Each symbol now shows realistic and different P&L values
- **Risk-Adjusted Sizing**: Position sizes appropriate for asset price levels
- **Drawdown Control**: Effective risk management prevents excessive losses
- **Sharpe Ratios**: Realistic performance metrics across market conditions

## Design Principles
- **Hexagonal Architecture**: Clear separation between business logic and external concerns
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Single Responsibility**: Each class has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Testability**: All components are designed to be easily testable
- **Risk Management**: Built-in constraints prevent excessive risk exposure



Key priorities:

Maintain architectural integrity
Prevent lag and performance issues
Avoid look-ahead problems
Eliminate other common failure patterns

Make sure everything remains fully functional after each major check.
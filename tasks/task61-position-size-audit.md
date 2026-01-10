You are a senior quantitative risk architect working on an enterprise hedge fund trading system.

I will provide you with an EnterpriseRiskManager module.

Your task is to:
1. Audit the current position sizing logic and explain clearly why position sizes vary unrealistically (e.g. $0.8 vs $5 trades).

2. Design a unified, professional position sizing architecture that:
   - Is fully consistent with risk_per_trade, stop_loss distance, and portfolio equity.
   - Supports a FIXED_POSITION_SIZE_ENABLED flag:
        - If enabled: position size must always be a fixed predefined dollar or unit value.
        - If disabled: position size must be calculated dynamically from risk % and stop loss.
   - Guarantees that risk per trade is mathematically controlled and consistent.

    ##############################
    # POSITION SIZING CONFIGURATION
    ##############################
    # Fixed Position Size Configuration (for testing purposes)
    FIXED_POSITION_SIZE_ENABLED=true      # Enable fixed position sizing (true/false)
    FIXED_POSITION_AMOUNT=10.0             # Fixed position amount in USD (e.g., $10 for testing)
    DEFAULT_ACCOUNT_BALANCE=10000.0        # Default account balance in USD (e.g., $10000 for production, $1000 for testing)

3. Refactor calculate_position_size so that:
   - There is exactly ONE authoritative sizing formula.
   - All caps and limits are expressed in portfolio-risk logic, not arbitrary asset price rules.
   - Risk amount, stop distance, and final size are always internally consistent.

4. Integrate the sizing logic with:
   - max_position_exposure
   - max_portfolio_exposure
   - max_risk_per_trade

5. Provide:
   - The corrected code implementation.
   - Clear explanation of each step.
   - A validation example with numbers.
   - How FIXED_POSITION_SIZE_ENABLED affects all calculations.

6. Do NOT rewrite the entire architecture. Only improve and correct the risk & sizing subsystem while preserving the current structure.


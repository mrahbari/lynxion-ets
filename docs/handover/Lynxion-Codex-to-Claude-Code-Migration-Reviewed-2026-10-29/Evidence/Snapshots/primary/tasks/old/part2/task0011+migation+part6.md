### NGDP Architecture Design Audit

The current strategy migration is complete.
The architecture is frozen.

Before implementing NGDP, perform an architectural audit only.
Do not create code yet.
Do not create new markdown files or documentation.
Report findings directly in chat.

Follow the four engineering questions:

1. What production problem does NGDP solve?
2. Why is NGDP necessary now?
3. Why are current RiskManager / position sizing mechanisms insufficient?
4. Why is the proposed NGDP design the simplest correct solution?

Audit the current system:

1. Identify current ownership of:
   - position sizing
   - leverage calculation
   - risk exposure
   - portfolio heat
   - correlation checks
   - drawdown protection
   - volatility adjustment

2. Verify whether RiskManager already owns any of these responsibilities.

3. Define the correct boundary:

   DecisionPipeline
   ↓
   ExecutionIntent
   ↓
   NGDP
   ↓
   RiskManager
   ↓
   Broker

   OR another simpler architecture.

4. NGDP must NOT:
   - generate trading signals
   - know strategy names
   - duplicate ExecutionConfirmationEngine logic
   - duplicate ExecutionOptimizer logic
   - contain broker/exchange logic

5. Identify reusable existing components before creating new ones.

6. Check whether existing domain objects need extension:
   - ExecutionIntent
   - Position
   - Risk parameters
   - Portfolio state

7. Prefer modifying existing code over creating new files.

8. If implementation requires new abstractions, justify why they are necessary.

After analysis provide:
- recommended NGDP responsibility boundary
- files/classes that need modification
- files/classes that should remain untouched
- migration risk assessment
- whether implementation can start safely.
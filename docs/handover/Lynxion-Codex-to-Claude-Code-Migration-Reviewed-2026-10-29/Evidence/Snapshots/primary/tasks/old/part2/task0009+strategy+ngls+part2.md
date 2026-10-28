Perform a domain-boundary review instead of a file-count optimization.

The objective is NOT to minimize the number of files.

The objective is to keep each production responsibility in its appropriate bounded context.

Review every newly introduced class and determine:

1. Which bounded context owns this responsibility?

Possible contexts include:

- Market Regime
- Market Structure
- Strategy
- Execution
- Broker
- Research

2. Is the current module ownership correct?

3. If not, propose moving the class into the correct existing module.

4. Avoid creating "miscellaneous" files such as mtf_engines.py that combine unrelated responsibilities.

5. Prefer cohesive modules over fewer files.

The goal is a production-ready codebase with clear ownership rather than the smallest possible repository.
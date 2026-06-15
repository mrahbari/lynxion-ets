#!/usr/bin/env python3
"""Shadow Deployment Runner - thin entry point (E2.T5.1).

Orchestration now lives in
:class:`application.use_cases.run_shadow_deployment.ShadowDeploymentUseCase`
and process I/O lives in :mod:`interface.cli.shadow_deployment`. This shim
delegates so existing invocations keep working unchanged. The runner no longer
imports infrastructure nor constructs adapters/services; all wiring happens in
the composition root.
"""

import os
import sys

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Backward-compatible entry point; delegates to the CLI shell."""
    from interface.cli.shadow_deployment import main as cli_main
    return cli_main()


if __name__ == "__main__":
    main()

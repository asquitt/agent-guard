#!/usr/bin/env python3
"""AgentGuard Functional Test Suite — thin wrapper.

The actual tests have been split into tests/functional/ modules.
Run with: python3 -m tests.functional
Or:       python3 tests/functional_test.py
"""

from tests.functional.__main__ import main

if __name__ == "__main__":
    main()

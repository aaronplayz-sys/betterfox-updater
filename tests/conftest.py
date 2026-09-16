"""
Shared pytest configuration.

Adds the project root to sys.path so `import update_betterfox` works when
running pytest from the tests/ directory or the project root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
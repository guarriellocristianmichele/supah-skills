# Skill scripts are Python, standard library only

The prose scanner and the memory gauge are Python with no third-party imports, so there is nothing to `pip install` and the same file runs on Windows, macOS and Linux. Node was the alternative, since `npx` users already have it, but the scanner is regex, Unicode and statistics work where Python's standard library is stronger, and a rewrite of working, tested code bought only one fewer runtime. The cost is that Windows users must install Python. The minimum version is set by ADR 0009.

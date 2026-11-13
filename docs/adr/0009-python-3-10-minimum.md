# Skill scripts need Python 3.10 or newer

The minimum moves from 3.8 to 3.10. Python 3.8 reached end of life in October 2024, and `actions/setup-python` has no 3.8 build for Ubuntu 26.04, so CI could test it only by pinning an older runner. The code scanner settles it: `ast` parses only the grammar of the interpreter that runs it, so on 3.8 every file using `match` would be unreadable. On 3.10, `match` parses; newer syntax (3.12 type parameters) still needs a newer interpreter, and the scanner reports such files as skipped instead of guessing.

## Considered options

- Stay on 3.8: rejected; the CI pin and the parsing gap both grow with time.
- 3.9: rejected; it still cannot parse `match`.
- 3.12 or later: rejected for now; long-term-support Linux distributions and older macOS installs still ship 3.10 and 3.11.

## Consequences

- CI tests 3.10 and 3.13 on `ubuntu-latest`, `windows-latest`, and 3.13 on `macos-latest`.
- Scripts may use 3.10 features (structural pattern matching, `X | Y` type unions, parenthesised context managers).

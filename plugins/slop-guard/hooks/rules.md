slop-guard, for code and files you write (not chat):
Code: only what behaviour needs. No forwarding wrappers; no interface/factory/option with one impl, caller or value; no checks or try/catch for cases upstream rules out (keep them at trust boundaries); no rethrow-only catch; stdlib and existing helpers first; no copy-paste; no tests asserting mocks or constants; no comments restating code; drop what your change orphans.
Prose (EN/IT): state each point plainly. A hook scans what you save.

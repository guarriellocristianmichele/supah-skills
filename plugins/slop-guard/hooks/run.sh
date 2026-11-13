# Runs guard.py with the first Python 3 that starts (python3 on macOS/Linux; python or py on Windows,
# where python3 can be the Microsoft Store stub). Stdin passes through to guard.py.
for p in python3 python py; do
  if "$p" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    exec "$p" "$(dirname "$0")/guard.py" "$@"
  fi
done
exit 0

#!/bin/sh

# Run pyauto with stub tools, each of which logs every argument it gets

pyauto="$(cd "$(dirname "$0")/.." && pwd)/pyauto"
tmp="$(mktemp -d)"

mkdir "$tmp/bin" "$tmp/src"
# A stub fails when STUB_FAIL names it
for tool in autopep8 autoflake isort pyflakes; do
    printf '#!/bin/sh\nfor arg in "$@"; do echo "%s: $arg"; done >> "%s/log"\n[ "$STUB_FAIL" != "%s" ]\n' "$tool" "$tmp" "$tool" > "$tmp/bin/$tool"
    chmod +x "$tmp/bin/$tool"
done

run_pyauto()
{
    rm -f "$tmp/log"
    (cd "$tmp/src" && PATH="$tmp/bin:$PATH" PYAUTO_SCRICT=0 "$pyauto" "$@")
}

check()
{
    # check <what> <expected> <actual>
    if [ "$2" != "$3" ]; then
        printf 'FAIL: %s\nexpected:\n%s\nactual:\n%s\n' "$1" "$2" "$3"
        exit 1
    fi
}

touch "$tmp/src/a.py" "$tmp/src/my file.py" "$tmp/src/"'$(touch${IFS}marker).py'

run_pyauto .
if [ -e "$tmp/src/marker" ]; then
    echo "FAIL: a file name ran as shell code"
    exit 1
fi
check "pyflakes gets each .py file in the dir" \
    "$(printf '%s\n' 'pyflakes: ./$(touch${IFS}marker).py' 'pyflakes: ./a.py' 'pyflakes: ./my file.py')" \
    "$(grep '^pyflakes: ' "$tmp/log" | LC_ALL=C sort)"
check "autopep8 gets each option" \
    "autopep8: --aggressive" \
    "$(grep -x 'autopep8: --aggressive' "$tmp/log")"

run_pyauto "my file.py"
check "pyflakes gets the file" \
    "pyflakes: my file.py" \
    "$(grep '^pyflakes: ' "$tmp/log")"

# A failed tool does not stop pyauto in non-strict mode
rm -f "$tmp/log"
(cd "$tmp/src" && PATH="$tmp/bin:$PATH" PYAUTO_SCRICT=0 STUB_FAIL=autopep8 "$pyauto" a.py)
check "exit code when autopep8 fails in non-strict mode" 0 "$?"
check "tools run when autopep8 fails in non-strict mode" \
    "$(printf '%s\n' autopep8 autoflake isort pyflakes)" \
    "$(cut -d: -f1 "$tmp/log" | uniq)"

# In strict mode, pyauto stops at the first tool that fails. It checks for
# changes with git, so the files are committed.
git -C "$tmp/src" init -q
git -C "$tmp/src" add -A
git -C "$tmp/src" -c user.name=u -c user.email=u@x commit -q -m init

tools_run=""
for failed in autopep8 autoflake isort pyflakes; do
    tools_run="$tools_run$failed
"
    rm -f "$tmp/log"
    (cd "$tmp/src" && PATH="$tmp/bin:$PATH" PYAUTO_SCRICT=1 STUB_FAIL=$failed "$pyauto" a.py)
    check "exit code when $failed fails" 1 "$?"
    check "tools run until $failed fails" "$(printf %s "$tools_run")" "$(cut -d: -f1 "$tmp/log" | uniq)"
done

rm -rf "$tmp"
echo ok

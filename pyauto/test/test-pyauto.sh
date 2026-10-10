#!/bin/sh

# Run pyauto with stub tools, each of which logs every argument it gets

pyauto="$(cd "$(dirname "$0")/.." && pwd)/pyauto"
tmp="$(mktemp -d)"

mkdir "$tmp/bin" "$tmp/src"
for tool in autopep8 autoflake isort pyflakes; do
    printf '#!/bin/sh\nfor arg in "$@"; do echo "%s: $arg"; done >> "%s/log"\n' "$tool" "$tmp" > "$tmp/bin/$tool"
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

rm -rf "$tmp"
echo ok

#!/usr/bin/env bash
# Install the built `yt` binary and the shell completions on Linux or macOS.
set -euo pipefail

cd "$(dirname "$0")"

binary=$(ls dist/yt-linux-* dist/yt-macos-* dist/yt 2>/dev/null | head -n 1 || true)
if [ -z "${binary}" ]; then
    echo "No binary found in dist/. Run: uv run python build.py" >&2
    exit 1
fi

prefix="${PREFIX:-/usr/local}"
echo "Installing ${binary} to ${prefix}/bin/yt"
sudo install -Dm755 "${binary}" "${prefix}/bin/yt"

if [ -d /usr/share/bash-completion/completions ]; then
    sudo install -Dm644 completions/yt.bash /usr/share/bash-completion/completions/yt
elif [ -d /etc/bash_completion.d ]; then
    sudo install -Dm644 completions/yt.bash /etc/bash_completion.d/yt
fi

for dir in "${prefix}/share/zsh/site-functions" /usr/share/zsh/site-functions; do
    if [ -d "${dir}" ]; then
        sudo install -Dm644 completions/yt.zsh "${dir}/_yt"
        break
    fi
done

if [ -d "${HOME}/.config/fish/completions" ]; then
    install -Dm644 completions/yt.fish "${HOME}/.config/fish/completions/yt.fish"
fi

echo "Done. Run 'yt --help' or 'yt --gui'."

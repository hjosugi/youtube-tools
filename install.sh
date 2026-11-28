#!/bin/sh
# Install or update `yt` on Linux and macOS: no Python, no sudo.
#
#   curl -fsSL https://raw.githubusercontent.com/hjosugi/youtube-tools/main/install.sh | sh
#
# Run it again to update. Optional settings:
#   YT_INSTALL_DIR  where the binary goes        (default: ~/.local/bin)
#   YT_VERSION      a release tag such as v1.1.0 (default: the latest release)
set -eu

repo="hjosugi/youtube-tools"
dir="${YT_INSTALL_DIR:-$HOME/.local/bin}"
data="${XDG_DATA_HOME:-$HOME/.local/share}"

case "$(uname -s)" in
    Linux) os=linux ;;
    Darwin) os=macos ;;
    *) echo "install.sh supports Linux and macOS. On Windows use install.ps1." >&2; exit 1 ;;
esac
case "$(uname -m)" in
    x86_64 | amd64) arch=x86_64 ;;
    arm64 | aarch64) arch=arm64 ;;
    *) echo "No prebuilt yt for $(uname -m). Run it from source: see the README." >&2; exit 1 ;;
esac

asset="yt-${os}-${arch}"
if [ -n "${YT_VERSION:-}" ]; then
    base="https://github.com/${repo}/releases/download/${YT_VERSION}"
else
    base="https://github.com/${repo}/releases/latest/download"
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "Downloading ${asset}..."
curl -fL --progress-bar "${base}/${asset}" -o "${work}/yt"

# Check the download against the release's checksum list.
if curl -fsSL "${base}/SHA256SUMS" -o "${work}/SHA256SUMS"; then
    expected="$(awk -v name="$asset" '$2 == name || $2 == "*" name { print $1 }' "${work}/SHA256SUMS")"
    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "${work}/yt" | awk '{ print $1 }')"
    else
        actual="$(shasum -a 256 "${work}/yt" | awk '{ print $1 }')"
    fi
    if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
        echo "The download does not match its checksum. Nothing was installed." >&2
        exit 1
    fi
fi

mkdir -p "$dir"
chmod 755 "${work}/yt"
mv -f "${work}/yt" "${dir}/yt"
echo "Installed $("${dir}/yt" --version) to ${dir}/yt"

# Linux: put yt in the application menu, so opening the UI needs no terminal at all.
if [ "$os" = linux ]; then
    apps="${data}/applications"
    mkdir -p "$apps"
    cat > "${apps}/yt.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=yt
GenericName=YouTube downloader
Comment=YouTube subtitles, MP3 and MP4 in one click
Comment[ja]=YouTube の字幕・MP3・MP4 をワンクリックで
Exec="${dir}/yt" ui
Icon=folder-download
Terminal=false
Categories=AudioVideo;Network;
DESKTOP
fi

# Shell completions, for the shells that have a per-user place for them.
if [ -d "$HOME/.config/fish" ]; then
    mkdir -p "$HOME/.config/fish/completions"
    curl -fsSL "${base}/yt.fish" -o "$HOME/.config/fish/completions/yt.fish" || true
fi
if command -v bash >/dev/null 2>&1; then
    completions="${data}/bash-completion/completions"
    mkdir -p "$completions"
    curl -fsSL "${base}/yt.bash" -o "${completions}/yt" || true
fi

case ":${PATH}:" in
    *":${dir}:"*) echo "Run: yt" ;;
    *) echo "Run: ${dir}/yt   (add ${dir} to PATH to type just: yt)" ;;
esac

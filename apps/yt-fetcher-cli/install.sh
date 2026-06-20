#!/bin/bash

# Ensure the binary is built first
if [ ! -f "dist/yt-fetch-cli" ]; then
    echo "Executable not found. Please run ./build.sh first!"
    exit 1
fi

echo "Installing yt-fetch-cli to /usr/local/bin..."
sudo cp dist/yt-fetch-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/yt-fetch-cli

echo "Installing bash/fish completions..."
# Bash completion
if [ -d "/usr/share/bash-completion/completions" ]; then
    sudo cp completions/yt-fetch-cli.bash /usr/share/bash-completion/completions/yt-fetch-cli
elif [ -d "/etc/bash_completion.d" ]; then
    sudo cp completions/yt-fetch-cli.bash /etc/bash_completion.d/yt-fetch-cli
fi

# Fish completion
if [ -d "$HOME/.config/fish/completions" ]; then
    cp completions/yt-fetch-cli.fish ~/.config/fish/completions/
fi

echo "✅ Installation complete!"
echo "You can now execute 'yt-fetch-cli' from anywhere."

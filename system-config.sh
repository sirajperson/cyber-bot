#!/bin/bash
#
# system-config.sh
#
# Installs Docker Engine and NVIDIA Container Toolkit on the host system.
# Requires root privileges (run with sudo).
#
# Usage: sudo ./system-config.sh <distribution>
# Supported distributions: debian, fedora, arch
#
# Prerequisites:
# 1. NVIDIA GPU drivers must be installed and working.
# 2. Internet connection.
#

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
NVIDIA_CONTAINER_TOOLKIT_VERSION="1.18.0-1" # As per NVIDIA docs example

# --- Helper Functions ---
print_usage() {
    echo "Usage: sudo $0 <distribution>"
    echo "Supported distributions: debian, fedora, arch"
    echo "Example: sudo $0 debian"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run as root (use sudo)."
        exit 1
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Docker Installation Functions ---

install_docker_debian() {
    echo ">>> Installing Docker Engine for Debian/Ubuntu..."
    # Add Docker's official GPG key:
    apt-get update
    apt-get install -y ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update

    # Install Docker packages
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Verify installation (optional, comment out if not needed)
    # docker run hello-world
    echo ">>> Docker Engine installed successfully for Debian/Ubuntu."
}

install_docker_fedora() {
    echo ">>> Installing Docker Engine for Fedora..."
    dnf -y install dnf-plugins-core
    dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker service
    systemctl start docker
    systemctl enable docker

    # Verify installation (optional, comment out if not needed)
    # docker run hello-world
    echo ">>> Docker Engine installed successfully for Fedora."
}

install_docker_arch() {
    echo ">>> Installing Docker Engine for Arch Linux..."
    pacman -Sy --noconfirm docker docker-compose

    # Start and enable Docker service
    systemctl start docker
    systemctl enable docker

    # Verify installation (optional, comment out if not needed)
    # docker run hello-world
    echo ">>> Docker Engine installed successfully for Arch Linux."
}

# --- NVIDIA Container Toolkit Installation Functions ---

install_nvidia_toolkit_debian() {
    echo ">>> Installing NVIDIA Container Toolkit for Debian/Ubuntu..."
    # Install prerequisites
    apt-get update && apt-get install -y --no-install-recommends \
       curl \
       gnupg2

    # Configure the production repository
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    # Update package list and install toolkit
    apt-get update
    apt-get install -y \
      nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-docker2 # Often included or resolves dependencies

    # Configure Docker runtime
    echo "Configuring Docker runtime..."
    nvidia-ctk runtime configure --runtime=docker

    # Restart Docker daemon
    echo "Restarting Docker service..."
    systemctl restart docker

    echo ">>> NVIDIA Container Toolkit installed and Docker configured successfully for Debian/Ubuntu."
}

install_nvidia_toolkit_fedora() {
    echo ">>> Installing NVIDIA Container Toolkit for Fedora..."
    # Install prerequisites
    dnf install -y \
       curl

    # Configure the production repository
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
      tee /etc/yum.repos.d/nvidia-container-toolkit.repo

    # Install the toolkit packages
    dnf install -y \
      nvidia-container-toolkit-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-container-toolkit-base-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container-tools-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container1-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-docker2 # Often included or resolves dependencies

    # Configure Docker runtime
    echo "Configuring Docker runtime..."
    nvidia-ctk runtime configure --runtime=docker

    # Restart Docker daemon
    echo "Restarting Docker service..."
    systemctl restart docker

    echo ">>> NVIDIA Container Toolkit installed and Docker configured successfully for Fedora."
}

install_nvidia_toolkit_arch() {
    echo ">>> Installing NVIDIA Container Toolkit for Arch Linux..."
    echo "Note: Ensure your NVIDIA drivers are correctly installed first."
    echo "Installing nvidia-container-toolkit package..."

    # Install the toolkit package (assuming it's in official repos or enabled community/multilib)
    pacman -Sy --noconfirm nvidia-container-toolkit

    # Configure Docker runtime
    echo "Configuring Docker runtime..."
    # The nvidia-ctk command might work, or manual config might be needed. Trying nvidia-ctk first.
    if command_exists nvidia-ctk; then
        nvidia-ctk runtime configure --runtime=docker
    else
        echo "Warning: nvidia-ctk command not found. You might need to manually configure /etc/docker/daemon.json for the NVIDIA runtime."
        echo "Refer to Arch Wiki or NVIDIA Container Toolkit documentation for manual configuration."
    fi

    # Restart Docker daemon
    echo "Restarting Docker service..."
    systemctl restart docker

    echo ">>> NVIDIA Container Toolkit installed for Arch Linux. Manual Docker configuration might be required if nvidia-ctk failed."
}


# --- Main Script Logic ---

check_root

# Check if distribution argument is provided
if [ -z "$1" ]; then
    echo "Error: Distribution argument missing."
    print_usage
    exit 1
fi

DISTRO=$(echo "$1" | tr '[:upper:]' '[:lower:]') # Convert to lowercase

case "$DISTRO" in
    debian|ubuntu)
        echo "Detected Debian/Ubuntu based system."
        if ! command_exists docker; then
            install_docker_debian
        else
            echo "Docker already installed. Skipping Docker installation."
        fi
        install_nvidia_toolkit_debian
        ;;
    fedora|rhel|centos|amazon) # Include common RPM bases
        echo "Detected Fedora/RPM based system."
         if ! command_exists docker; then
            install_docker_fedora
        else
            echo "Docker already installed. Skipping Docker installation."
        fi
        install_nvidia_toolkit_fedora
        ;;
    arch)
        echo "Detected Arch Linux based system."
         if ! command_exists docker; then
            install_docker_arch
        else
            echo "Docker already installed. Skipping Docker installation."
        fi
        install_nvidia_toolkit_arch
        ;;
    *)
        echo "Error: Unsupported distribution '$1'."
        print_usage
        exit 1
        ;;
esac

echo "--- System Configuration Complete ---"
echo "You should now be able to run Docker containers with GPU access using '--gpus all'."
echo "Test with: sudo docker run --rm --gpus all nvidia/cuda:12.6.0-base-debian12 nvidia-smi"

exit 0

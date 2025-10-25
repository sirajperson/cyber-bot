# Use Kali Linux as the base image
FROM kalilinux/kali-rolling

# Set non-interactive frontend for package installations
ENV DEBIAN_FRONTEND=noninteractive

# (Optional but good practice) Ensure contrib and non-free are enabled
# RUN sed -i 's/main$/main contrib non-free non-free-firmware/' /etc/apt/sources.list

# Update package lists and install basic dependencies + Python 3.12 + Browser
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    git \
    curl \
    wget \
    gnupg2 \
    # --- Browser for Selenium ---
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Install common Kali Linux tools needed by the crews
# Using kali-linux-large covers many tools. Add specifics if needed.
# Note: This increases image size significantly. Consider kali-linux-default + specifics.
RUN apt-get update && apt-get install -y --no-install-recommends \
    kali-linux-large \
    # --- Ensure specific tools are present ---
    nmap \
    hashcat \
    john \
    ghidra \
    volatility3 \
    binwalk \
    foremost \
    steghide \
    exiftool \
    tshark \
    sqlmap \
    gobuster \
    dirb \
    nikto \
    nuclei \
    # Python libs often needed by tools or scripts
    python3-cryptography \
    python3-pycryptodome \
    # Metasploit is very large, uncomment if absolutely required
    # metasploit-framework \
    && rm -rf /var/lib/apt/lists/*

# --- Install NVIDIA CUDA Toolkit 12.6 ---
# (Include this if any part of your workflow might use GPU, otherwise optional)
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i cuda-keyring_1.1-1_all.deb \
    && rm cuda-keyring_1.1-1_all.deb \
    && apt-get update \
    # Install runtime libraries, add -dev if compiling CUDA code needed
    && apt-get install -y --no-install-recommends cuda-toolkit-12-6 \
    && rm -rf /var/lib/apt/lists/*

# Set CUDA environment variables
ENV PATH=/usr/local/cuda-12.6/bin${PATH:+:${PATH}}
ENV LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
# Ensure nvidia-container-toolkit compatibility
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Set the working directory in the container
WORKDIR /app

# Copy dependency definition files first for layer caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
# Using --system installs globally, accessible without virtual env activation
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the rest of the application code
COPY . .

# (Optional) Expose any ports if your application runs a web service
# EXPOSE 8000

# Set the default command to run the Cyber Bot
CMD ["uv", "run", "-m", "src.main"]


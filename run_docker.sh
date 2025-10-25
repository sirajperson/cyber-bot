#!/bin/bash
#
# run_docker.sh
#
# This script builds (if necessary) and runs the Docker container
# for the Cyber Bot project.
#
# It mounts the necessary local directories (.env, data, logs) into the
# container and enables GPU access.
#

# --- Configuration ---
IMAGE_NAME="cyber-bot-kali:latest"
PROJECT_ROOT=$(pwd) # Assumes the script is run from the project root

# --- Check if image exists, build if not ---
if [[ "$(docker images -q ${IMAGE_NAME} 2> /dev/null)" == "" ]]; then
  echo "Docker image '${IMAGE_NAME}' not found. Building..."
  # Build the image using the Dockerfile in the current directory
  docker build -t ${IMAGE_NAME} .
  if [ $? -ne 0 ]; then
    echo "Docker build failed. Exiting."
    exit 1
  fi
  echo "Docker image built successfully."
else
  echo "Using existing Docker image: ${IMAGE_NAME}"
fi

# --- Run the Container ---
echo "Running the Cyber Bot container..."
echo "Mounting .env file from: ${PROJECT_ROOT}/.env"
echo "Mounting data directory from: ${PROJECT_ROOT}/data"
echo "Mounting logs directory from: ${PROJECT_ROOT}/logs"
echo "Enabling GPU access (requires nvidia-container-toolkit)"

# Ensure data and logs directories exist locally before mounting
mkdir -p "${PROJECT_ROOT}/data"
mkdir -p "${PROJECT_ROOT}/logs"

# Execute the docker run command
docker run --rm -it \
  --gpus all \
  -v "${PROJECT_ROOT}/.env:/app/.env:ro" \
  -v "${PROJECT_ROOT}/data:/app/data" \
  -v "${PROJECT_ROOT}/logs:/app/logs" \
  ${IMAGE_NAME}

# Check the exit status of the docker command
EXIT_STATUS=$?
if [ ${EXIT_STATUS} -ne 0 ]; then
    echo "Docker container exited with status ${EXIT_STATUS}."
else
    echo "Docker container finished successfully."
fi

exit ${EXIT_STATUS}

#!/bin/bash
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/manual_package.sh
echo "Creating package for P2P Messenger..."

# Визначаємо директорії
LAUNCHER_DIR="$(pwd)"
PROJECT_DIR="$(dirname "$LAUNCHER_DIR")"
OUTPUT_DIR="${PROJECT_DIR}/website/downloads"
BUILD_DIR="${LAUNCHER_DIR}/build_manual"

# Створюємо директорії
rm -rf "${BUILD_DIR}" 2>/dev/null
mkdir -p "${BUILD_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Копіюємо файли з клієнту
cp "${PROJECT_DIR}/client/user-docker-compose.yml" "${BUILD_DIR}/docker-compose.yml"
cp "${PROJECT_DIR}/client/.env" "${BUILD_DIR}/"

# Копіюємо необхідні файли для Docker
cp -r "${PROJECT_DIR}/client/docker" "${BUILD_DIR}/"
cp -r "${PROJECT_DIR}/client/backend" "${BUILD_DIR}/"
cp -r "${PROJECT_DIR}/client/frontend" "${BUILD_DIR}/"
cp "${PROJECT_DIR}/client/requirements.txt" "${BUILD_DIR}/" 2>/dev/null

# Копіюємо лаунчер і допоміжні файли
cp "${LAUNCHER_DIR}/messenger_launcher_simple.py" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/start.command" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/README.txt" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/Create Launcher.command" "${BUILD_DIR}/"

# Робимо файли виконуваними
chmod +x "${BUILD_DIR}/start.command"
chmod +x "${BUILD_DIR}/Create Launcher.command"

# Створюємо ZIP-архів
cd "${BUILD_DIR}"
zip -r "${OUTPUT_DIR}/P2P_Messenger_macOS_Simple.zip" *

echo "Package created: ${OUTPUT_DIR}/P2P_Messenger_macOS_Simple.zip"
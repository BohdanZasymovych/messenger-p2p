#!/bin/bash
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/create_linux_package.sh
echo "Creating Linux package for P2P Messenger..."

# Визначаємо директорії
LAUNCHER_DIR="$(pwd)"
PROJECT_DIR="$(dirname "$LAUNCHER_DIR")"
OUTPUT_DIR="${PROJECT_DIR}/website/downloads"
BUILD_DIR="${LAUNCHER_DIR}/build_linux"

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

# Копіюємо створені Linux-файли в бібліотеку
cp "${LAUNCHER_DIR}/linux/start.sh" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/linux/Create_Launcher.sh" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/linux/clean_docker.sh" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/linux/access_db.sh" "${BUILD_DIR}/"
cp "${LAUNCHER_DIR}/linux/README.txt" "${BUILD_DIR}/"

# Копіюємо месенджер лаунчер
cp "${LAUNCHER_DIR}/messenger_launcher_simple.py" "${BUILD_DIR}/"

# Робимо скрипти виконуваними
chmod +x "${BUILD_DIR}/start.sh"
chmod +x "${BUILD_DIR}/Create_Launcher.sh"
chmod +x "${BUILD_DIR}/clean_docker.sh"
chmod +x "${BUILD_DIR}/access_db.sh"

# Створюємо ZIP-архів
cd "${BUILD_DIR}"
zip -r "${OUTPUT_DIR}/P2P_Messenger_Linux.zip" *

echo "Package created: ${OUTPUT_DIR}/P2P_Messenger_Linux.zip"
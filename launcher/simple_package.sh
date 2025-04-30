#!/bin/bash
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/simple_package.sh

echo "Packaging simplified P2P Messenger for macOS..."

# Визначаємо директорії
LAUNCHER_DIR="$(pwd)"
PROJECT_DIR="$(dirname "$LAUNCHER_DIR")"
OUTPUT_DIR="${PROJECT_DIR}/website/downloads"
BUILD_DIR="${LAUNCHER_DIR}/build_simple"

# Створюємо директорії
mkdir -p "${BUILD_DIR}"
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${BUILD_DIR}/docker"

# Копіюємо файли Docker Compose
echo "Copying Docker Compose files..."
cp "${PROJECT_DIR}/client/user-docker-compose.yml" "${BUILD_DIR}/docker-compose.yml"
cp "${PROJECT_DIR}/client/.env" "${BUILD_DIR}/"
cp -r "${PROJECT_DIR}/client/docker" "${BUILD_DIR}/"

# Копіюємо launcher
cp "${LAUNCHER_DIR}/messenger_launcher.py" "${BUILD_DIR}/"

# Створюємо README
cat > "${BUILD_DIR}/README.txt" << EOF
P2P Messenger - Інструкція з використання
=========================================

1. Встановіть Docker Desktop з сайту docker.com
2. Запустіть програму P2P Messenger (подвійний клік на start.command)
3. Дочекайтесь запуску додатку у браузері

Якщо у вас виникли проблеми, відкрийте браузер і перейдіть 
за адресою: http://localhost:8000

Для зупинки програми, натисніть Ctrl+C в консолі або закрийте 
термінал і виконайте команду:
docker-compose -f docker-compose.yml down
EOF

# Створюємо запускальний файл
cat > "${BUILD_DIR}/start.command" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
python3 messenger_launcher.py
EOF

# Робимо файл запускальним
chmod +x "${BUILD_DIR}/start.command"

# Створюємо ZIP-архів
cd "${BUILD_DIR}"
zip -r "${OUTPUT_DIR}/P2P_Messenger_macOS_Simple.zip" *

echo "Спрощений пакет створено: ${OUTPUT_DIR}/P2P_Messenger_macOS_Simple.zip"
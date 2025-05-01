#!/bin/bash
cd "$(dirname "$0")"

# Створюємо AppleScript
cat > "./P2P Messenger Launcher.applescript" << EOL
tell application "Terminal"
    do script "cd '$(pwd)' && python3 messenger_launcher_simple.py"
    activate
end tell
EOL

# Компілюємо AppleScript у додаток
osacompile -o "./P2P Messenger.app" "./P2P Messenger Launcher.applescript"

# Видаляємо вихідний файл
rm "./P2P Messenger Launcher.applescript"

echo "Лаунчер успішно створено!"
echo "Тепер ви можете перенести 'P2P Messenger.app' в теку Applications або на робочий стіл."
echo "Натисніть Enter для завершення..."
read
#!/bin/bash
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/linux/Create_Launcher.sh
cd "$(dirname "$0")"

# Створюємо десктопний файл запуску
cat > "P2P_Messenger.desktop" << EOF
[Desktop Entry]
Type=Application
Name=P2P Messenger
Exec=bash -c "cd '$(pwd)' && ./start.sh"
Icon=
Terminal=true
Categories=Network;Chat;
Comment=P2P Messenger з шифруванням
EOF

chmod +x "P2P_Messenger.desktop"

echo "Лаунчер успішно створено!"
echo "Тепер ви можете скопіювати 'P2P_Messenger.desktop' в ~/.local/share/applications/ для додавання в меню програм"
echo "Або просто запускати його подвійним кліком з файлового менеджера"
echo "Натисніть Enter для завершення..."
read
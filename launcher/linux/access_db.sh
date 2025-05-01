#!/bin/bash
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/linux/access_db.sh
cd "$(dirname "$0")"

echo "Перевірка статусу контейнера бази даних..."
DB_STATUS=$(docker inspect --format="{{.State.Status}}" messenger_user_db 2>/dev/null)

if [ "$DB_STATUS" != "running" ]; then
    echo "Контейнер бази даних не запущено. Запускаю..."
    docker start messenger_user_db
    
    if [ $? -ne 0 ]; then
        echo "Помилка запуску контейнера бази даних."
        echo "Натисніть Enter для виходу..."
        read
        exit 1
    fi
fi

echo "Підключення до бази даних..."
docker exec -it messenger_user_db psql -U messenger_user -d messenger_user_db

echo "Сеанс бази даних завершено."
echo "Натисніть Enter для виходу..."
read
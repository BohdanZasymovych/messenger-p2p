#!/usr/bin/env python3
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/messenger_launcher_simple.py
import os
import sys
import time
import webbrowser
import subprocess
import platform

# Визначення констант
APP_NAME = "P2P Messenger"
APP_VERSION = "1.0.0"
DOCKER_NETWORK = "messenger_network"

def print_header():
    print(f"""
╔═══════════════════════════════════════════╗
║             {APP_NAME} {APP_VERSION}               ║
║                                           ║
║  P2P месенджер з шифруванням              ║
╚═══════════════════════════════════════════╝
""")

def check_docker():
    try:
        docker_process = subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if docker_process.returncode != 0:
            return False, "Docker не встановлено"
            
        compose_process = subprocess.run(["docker", "compose", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if compose_process.returncode != 0:
            old_compose_process = subprocess.run(["docker-compose", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if old_compose_process.returncode != 0:
                return False, "Docker Compose не встановлено"
        
        return True, "Docker і Docker Compose встановлені"
    except Exception as e:
        return False, f"Помилка під час перевірки Docker: {str(e)}"

def docker_command():
    process = subprocess.run(["docker", "compose", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode == 0:
        return ["docker", "compose"]
    else:
        return ["docker-compose"]

def create_docker_network():
    try:
        network_check = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        networks = network_check.stdout.strip().split('\n')
        if DOCKER_NETWORK not in networks:
            print(f"Створення Docker мережі '{DOCKER_NETWORK}'...")
            subprocess.run(["docker", "network", "create", DOCKER_NETWORK], check=True)
            print(f"Мережа '{DOCKER_NETWORK}' успішно створена.")
        else:
            print(f"Мережа '{DOCKER_NETWORK}' вже існує.")
            
        return True
    except Exception as e:
        print(f"Помилка створення Docker мережі: {str(e)}")
        return False

def check_containers_status():
    """Перевіряє статус контейнерів і запускає їх, якщо потрібно"""
    try:
        # Перевірка контейнера messenger_user_db
        db_check = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=messenger_user_db", "--format", "{{.Status}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Перевірка контейнера messenger_app
        app_check = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=messenger_app", "--format", "{{.Status}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        db_status = db_check.stdout.strip()
        app_status = app_check.stdout.strip()
        
        # Якщо обидва контейнери не знайдені, це перший запуск
        if not db_status and not app_status:
            print("Контейнери не знайдені. Перший запуск додатку.")
            return "first_run"
        
        # Якщо контейнери зупинені
        if db_status and not db_status.startswith("Up"):
            print("База даних зупинена. Запуск...")
            subprocess.run(["docker", "start", "messenger_user_db"], check=False)
        
        if app_status and not app_status.startswith("Up"):
            print("Додаток зупинений. Запуск...")
            subprocess.run(["docker", "start", "messenger_app"], check=False)
            
        # Якщо контейнери запущені
        if (db_status and db_status.startswith("Up")) and (app_status and app_status.startswith("Up")):
            print("Контейнери вже запущені.")
            return "running"
            
        # Якщо хоча б один контейнер запущений
        if (db_status and db_status.startswith("Up")) or (app_status and app_status.startswith("Up")):
            print("Деякі контейнери запущені. Запуск інших...")
            return "partial"
        
        # Якщо контейнери існують, але зупинені
        return "stopped"
    except Exception as e:
        print(f"Помилка перевірки контейнерів: {e}")
        return "error"

def check_volumes():
    """Перевіряє наявність томів для збереження даних"""
    try:
        # Перевірка томів
        volumes_check = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        volumes = volumes_check.stdout.strip().split('\n')
        
        # Використовуємо точні назви томів із docker-compose.yml
        required_volumes = [
            "p2p_messenger_macos_postgres_data_user",
            "p2p_messenger_macos_encryption_keys",
            "p2p_messenger_macos_message_data"
        ]
        
        missing_volumes = []
        for volume in required_volumes:
            found = False
            for v in volumes:
                if volume in v:
                    found = True
                    break
            if not found:
                missing_volumes.append(volume)
        
        if missing_volumes:
            print(f"Відсутні томи: {', '.join(missing_volumes)}")
            return False
        else:
            print("Всі необхідні томи знайдені.")
            return True
    except Exception as e:
        print(f"Помилка перевірки томів: {e}")
        return False

def start_docker_compose():
    """Запускає docker-compose"""
    try:
        compose_cmd = docker_command()
        
        print("Запуск Docker Compose...")
        print(f"Поточна директорія: {os.getcwd()}")
        
        if not os.path.exists("docker-compose.yml"):
            print("Помилка: Не знайдено файл docker-compose.yml")
            return False
        
        # Перевірка статусу контейнерів
        status = check_containers_status()
        
        # Перевіряємо наявність томів
        volumes_exist = check_volumes()
        
        # Якщо це перший запуск або відсутні томи, запускаємо повну збірку
        if status == "first_run" or not volumes_exist:
            print("Перший запуск або відсутні томи. Запуск повної збірки контейнерів...")
            # ВАЖЛИВО: Використовуємо up з --no-recreate, щоб не перестворювати контейнери, якщо вони вже існують
            build_process = subprocess.run(
                compose_cmd + ["up", "-d", "--build", "--no-recreate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if build_process.returncode != 0:
                print("Помилка запуску Docker Compose:")
                print(build_process.stderr)
                return False
                
        # Якщо контейнери зупинені, просто запускаємо їх
        elif status == "stopped":
            print("Запуск зупинених контейнерів...")
            subprocess.run(
                compose_cmd + ["start"],
                check=False
            )
            
        # Якщо частина контейнерів запущена або була помилка
        elif status in ["partial", "error"]:
            print("Запуск всіх контейнерів (без перестворення)...")
            subprocess.run(
                compose_cmd + ["up", "-d", "--no-recreate"],
                check=False
            )
            
        print("Docker Compose успішно запущено")
        return True
    except Exception as e:
        print(f"Помилка запуску Docker Compose: {e}")
        return False

def check_app_status():
    """Перевіряє статус запущених контейнерів"""
    try:
        print("\nСтатус запущених контейнерів:")
        subprocess.run(["docker", "ps"], check=False)
        
        app_check = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", "messenger_app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if app_check.returncode == 0 and app_check.stdout.strip() == "running":
            print("Контейнер messenger_app запущено та працює.")
            return True
        else:
            print("Контейнер messenger_app НЕ запущено або він не працює.")
            print("Виведення логів messenger_app:")
            subprocess.run(
                ["docker", "logs", "messenger_app"],
                check=False
            )
            return False
    except Exception as e:
        print(f"Помилка перевірки статусу додатку: {e}")
        return False

def open_browser():
    """Відкриває браузер з додатком"""
    try:
        print("Очікування запуску додатку (15 секунд)...")
        time.sleep(15)
        
        if not check_app_status():
            choice = input("Додаток може бути не готовий. Все одно відкрити браузер? (y/n): ")
            if choice.lower() != 'y':
                return False
        
        url = "http://localhost:8000"
        print(f"Відкриваю {url} у браузері...")
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"Помилка відкриття браузера: {e}")
        return False

def stop_containers():
    """Зупиняє контейнери без їх видалення"""
    try:
        compose_cmd = docker_command()
        
        print("Зупинка контейнерів...")
        # ВАЖЛИВО: Використовуємо stop замість down, щоб не видаляти контейнери і томи
        subprocess.run(
            compose_cmd + ["stop"],
            check=False
        )
        
        print("Контейнери зупинено, дані збережено")
        return True
    except Exception as e:
        print(f"Помилка зупинки контейнерів: {e}")
        return False

def main():
    print_header()
    
    docker_installed, message = check_docker()
    print(message)
    
    if not docker_installed:
        print("Docker не встановлено. Встановіть Docker Desktop з сайту docker.com")
        input("Натисніть Enter для виходу...")
        return
    
    if not create_docker_network():
        input("Натисніть Enter для виходу...")
        return
    
    if not start_docker_compose():
        input("Натисніть Enter для виходу...")
        return
    
    open_browser()
    
    print("\nДодаток запущено і працює в фоновому режимі.")
    print("Щоб зупинити додаток, введіть 'exit' або натисніть Ctrl+C.")
    print("Ваші дані будуть збережені між запусками.")
    
    try:
        while True:
            command = input("\nВведіть 'exit' для завершення: ")
            if command.lower() == 'exit':
                break
    except KeyboardInterrupt:
        print("\nОтримано сигнал завершення.")
    
    stop_containers()
    print("\nДякуємо за використання P2P Messenger!")

if __name__ == "__main__":
    main()
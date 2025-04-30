#!/usr/bin/env python3
# filepath: /Users/user/Documents/OP_2/messenger-p2p/launcher/messenger_launcher.py
import os
import sys
import time
import webbrowser
import subprocess
import platform
from pathlib import Path
import shutil

# Визначення констант
APP_NAME = "P2P Messenger"
APP_VERSION = "1.0.0"
DOCKER_NETWORK = "messenger_network"

def print_header():
    """Виводить заголовок програми"""
    print(f"""
╔═══════════════════════════════════════════╗
║             {APP_NAME} {APP_VERSION}               ║
║                                           ║
║  P2P месенджер з шифруванням              ║
╚═══════════════════════════════════════════╝
""")

def check_docker():
    """Перевіряє чи встановлений Docker і Docker Compose"""
    try:
        # Перевірка Docker
        docker_process = subprocess.run(
            ["docker", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if docker_process.returncode != 0:
            return False, "Docker не встановлено"
            
        # Перевірка Docker Compose
        compose_process = subprocess.run(
            ["docker", "compose", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if compose_process.returncode != 0:
            # Спробувати стару команду docker-compose
            old_compose_process = subprocess.run(
                ["docker-compose", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            if old_compose_process.returncode != 0:
                return False, "Docker Compose не встановлено"
        
        return True, "Docker і Docker Compose встановлені"
    except Exception as e:
        return False, f"Помилка під час перевірки Docker: {str(e)}"

def docker_command():
    """Повертає правильну команду для Docker Compose"""
    # Перевірка нової команди docker compose
    compose_process = subprocess.run(
        ["docker", "compose", "--version"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    if compose_process.returncode == 0:
        return ["docker", "compose"]
    else:
        return ["docker-compose"]

def create_docker_network():
    """Створює Docker мережу, якщо вона ще не існує"""
    try:
        # Перевірка, чи мережа вже існує
        network_check = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        networks = network_check.stdout.strip().split('\n')
        if DOCKER_NETWORK not in networks:
            print(f"Створення Docker мережі '{DOCKER_NETWORK}'...")
            subprocess.run(
                ["docker", "network", "create", DOCKER_NETWORK],
                check=True
            )
            print(f"Мережа '{DOCKER_NETWORK}' успішно створена.")
        else:
            print(f"Мережа '{DOCKER_NETWORK}' вже існує.")
            
        return True
    except Exception as e:
        print(f"Помилка створення Docker мережі: {str(e)}")
        return False

def start_client():
    """Запускає клієнтський додаток"""
    compose_cmd = docker_command()
    
    try:
        print("Запуск клієнтського додатку...")
        
        compose_file = Path("docker-compose.yml")
        if not compose_file.exists():
            print(f"Помилка: Файл docker-compose.yml не знайдено. Перевірте, чи знаходитесь ви в директорії з програмою.")
            return False
        
        # Зупинити попередні контейнери, якщо вони запущені
        stop_process = subprocess.run(
            compose_cmd + ["-f", "docker-compose.yml", "down"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Запустити контейнери
        subprocess.Popen(
            compose_cmd + ["-f", "docker-compose.yml", "up"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("Клієнтський додаток запущено.")
        return True
    except Exception as e:
        print(f"Помилка запуску клієнтського додатку: {str(e)}")
        return False

def open_browser():
    """Відкриває браузер з додатком"""
    try:
        # Почекати, поки додаток запуститься
        print("Очікування запуску додатку (10 секунд)...")
        time.sleep(10)
        
        url = "http://localhost:8000"
        print(f"Відкриваю {url} у браузері...")
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"Помилка відкриття браузера: {str(e)}")
        return False

def stop_containers():
    """Зупиняє всі контейнери"""
    compose_cmd = docker_command()
    
    try:
        print("Зупинка контейнерів...")
        compose_file = Path("docker-compose.yml")
        if compose_file.exists():
            subprocess.run(
                compose_cmd + ["-f", "docker-compose.yml", "down"],
                check=False
            )
        
        print("Всі контейнери зупинено.")
        return True
    except Exception as e:
        print(f"Помилка зупинки контейнерів: {str(e)}")
        return False

def install_docker_instructions():
    """Виводить інструкції з встановлення Docker"""
    print("\nДля роботи додатку потрібен Docker Desktop.")
    print("Будь ласка, встановіть Docker Desktop за посиланням:")
    
    system = platform.system()
    if system == "Windows":
        print("  https://docs.docker.com/desktop/install/windows-install/")
    elif system == "Darwin":  # macOS
        print("  https://docs.docker.com/desktop/install/mac-install/")
    elif system == "Linux":
        print("  https://docs.docker.com/desktop/install/linux-install/")
    
    print("\nПісля встановлення Docker Desktop, запустіть цю програму знову.")
    
    # Спробувати відкрити сторінку в браузері
    try:
        open_url = input("Відкрити сторінку встановлення у браузері? (y/n): ").lower()
        if open_url == 'y':
            if system == "Windows":
                webbrowser.open("https://docs.docker.com/desktop/install/windows-install/")
            elif system == "Darwin":
                webbrowser.open("https://docs.docker.com/desktop/install/mac-install/")
            elif system == "Linux":
                webbrowser.open("https://docs.docker.com/desktop/install/linux-install/")
    except:
        pass

def main():
    """Головна функція програми"""
    print_header()
    
    # Вивести інформацію про поточну директорію
    print(f"Поточна директорія: {os.getcwd()}")
    print(f"Файли в поточній директорії: {os.listdir('.')}")
    
    # Перевірка Docker
    docker_installed, message = check_docker()
    print(message)
    
    if not docker_installed:
        install_docker_instructions()
        input("\nНатисніть Enter для виходу...")
        return
    
    # Створення Docker мережі
    if not create_docker_network():
        input("\nНатисніть Enter для виходу...")
        return
    
    # Запуск додатку
    if not start_client():
        input("\nНатисніть Enter для виходу...")
        return
    
    # Відкриття браузера
    open_browser()
    
    print("\nДодаток запущено і працює в фоновому режимі.")
    print("Щоб зупинити додаток, введіть 'exit' або натисніть Ctrl+C.")
    
    # Очікування на команду завершення
    try:
        while True:
            command = input("\nВведіть 'exit' для завершення: ")
            if command.lower() == 'exit':
                break
    except KeyboardInterrupt:
        print("\nОтримано сигнал завершення.")
    
    # Зупинка контейнерів
    stop_containers()
    print("\nДякуємо за використання P2P Messenger!")

if __name__ == "__main__":
    main()
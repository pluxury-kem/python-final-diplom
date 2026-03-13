#!/bin/bash

# reset_migrations.sh - Полный сброс миграций и базы данных

echo "========================================="
echo "🔄 СБРОС МИГРАЦИЙ И БАЗЫ ДАННЫХ"
echo "========================================="

# Деактивируем виртуальное окружение если активно
deactivate 2>/dev/null

# Бэкап базы данных
if [ -f db.sqlite3 ]; then
    echo "📦 Создание бэкапа базы данных..."
    BACKUP_NAME="db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)"
    cp db.sqlite3 "$BACKUP_NAME"
    echo "   Бэкап создан: $BACKUP_NAME"
fi

# Удаляем базу данных
echo "🗑️  Удаление базы данных..."
rm -f db.sqlite3

# Удаляем все миграции
echo "🗑️  Удаление файлов миграций..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "   Виртуальное окружение активировано"
else
    echo "❌ Виртуальное окружение не найдено!"
    exit 1
fi

# Проверяем наличие manage.py
if [ ! -f "manage.py" ]; then
    echo "❌ Файл manage.py не найден!"
    exit 1
fi

# Создаем новые миграции в правильном порядке
echo "📝 Создание миграций..."
echo "   Создание миграций users..."
python manage.py makemigrations users

echo "   Создание миграций shops..."
python manage.py makemigrations shops

echo "   Создание миграций products..."
python manage.py makemigrations products

echo "   Создание миграций orders_app..."
python manage.py makemigrations orders_app

# Применяем миграции
echo "🚀 Применение миграций..."
python manage.py migrate

# Проверяем результат
if [ $? -eq 0 ]; then
    echo "✅ Миграции успешно применены!"
    
    # Создаем суперпользователя
    echo "👤 Создание суперпользователя..."
    echo "   Введите email и пароль для суперпользователя:"
    python manage.py createsuperuser
    
    echo "========================================="
    echo "✅ ГОТОВО! База данных и миграции настроены"
    echo "========================================="
    echo ""
    echo "Для запуска сервера выполните:"
    echo "  python manage.py runserver"
    echo ""
    echo "Для тестирования выполните:"
    echo "  python test_api.py"
else
    echo "❌ Ошибка при применении миграций!"
    exit 1
fi

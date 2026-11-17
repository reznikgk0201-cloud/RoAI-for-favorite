Ro AI for favorite — стартовая версия

Состав:
- app.py — веб-приложение
- requirements.txt — зависимости Python
- .env.example — пример настроек (секреты сюда не вписывать для GitHub)

Локальный запуск:
1. Установить Python 3.11+
2. В терминале в папке проекта выполнить:
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
3. Задать переменные окружения:
   ROAI_SECRET_KEY = длинная случайная строка
   ROAI_ADMIN_USERNAME = Masya_show
   ROAI_ADMIN_EMAIL = твой email администратора
   ROAI_ADMIN_PASSWORD = длинный уникальный пароль
4. Запуск:
   python app.py

Render:
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT

ВАЖНО:
- Не публикуй пароли, секретные ключи или настоящий .env в GitHub.
- Это стартовый прототип. SQLite-файл на бесплатном Render может пропасть при перезапуске/переразмещении.
  Для настоящего сайта с постоянными аккаунтами подключи постоянную базу данных (например PostgreSQL).
- Промокоды пока не начисляют бонусы; подтверждение email и восстановление пароля не реализованы.
- Админ создаётся при первом запуске только если заданы ROAI_ADMIN_EMAIL и ROAI_ADMIN_PASSWORD.

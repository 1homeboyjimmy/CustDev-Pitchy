# Откат авторизации кастдева на общий APP_SECRET_KEY

Этот документ описывает возврат с текущего fallback-варианта (проверка общей
HttpOnly-сессии через `https://pitchy.pro/me`) на первоначальную схему, в которой
кастдев самостоятельно проверяет JWT тем же `APP_SECRET_KEY`, что и основной
Pitchy.

## Что должно быть выполнено на сервере

1. Получить фактическое значение `APP_SECRET_KEY` основного Pitchy безопасным
   способом. Не вставлять секрет в git, workflow-логи или этот документ.
2. Убедиться, что в `/root/CustDev-Pitchy/.env` на production задано то же
   значение, например:

   ```dotenv
   APP_SECRET_KEY=<тот_же_секрет_что_у_основного_Pitchy>
   ```

3. Проверить, что длина секрета не меньше 32 символов. После деплоя убедиться,
   что контейнер кастдева действительно загрузил этот `.env`.

## Изменения в коде

В `backend/app/utils/auth.py`:

1. Удалить импорт `requests`.
2. Удалить функцию `verify_remote_session`.
3. В `authenticate_request()` заменить финальную часть:

   ```python
   local_payload = verify_jwt(token)
   return local_payload or (verify_remote_session(token) if cookie_token else None)
   ```

   на:

   ```python
   return verify_jwt(token)
   ```

В `backend/app/config.py` удалить параметры `MAIN_AUTH_URL` и
`MAIN_AUTH_TIMEOUT`.

В `backend/tests/test_custdev_regressions.py` удалить импорт `auth` и тест
`test_remote_main_auth_fallback_maps_user`.

## Изменения в workflow

В `.github/workflows/deploy-main.yml` можно вернуть блок синхронизации только
если runner действительно имеет доступ к `/opt/ai-startup/.env`. Блок должен
передавать исключительно `APP_SECRET_KEY`, не печатать его и не копировать весь
файл. Если такого доступа нет, оставьте workflow без синхронизации и задайте
секрет в `/root/CustDev-Pitchy/.env` вручную.

После изменений:

```powershell
cd C:\Users\s4nya\pitchy\CustDev-Pitchy\backend
.\.audit-venv\Scripts\python.exe -m pytest -q tests/test_custdev_regressions.py
```

Затем закоммитьте изменения, отправьте их в `main` и дождитесь успешного
workflow `Deploy to Production Server`. Проверка в браузере должна выполняться
в уже авторизованной сессии основного сайта: кнопка кастдева не должна
перенаправлять на `/login`.

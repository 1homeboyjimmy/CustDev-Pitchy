# CustDev SSO bridge

CustDev не должен делить с основным Pitchy `APP_SECRET_KEY` и не должен
проверять или хранить основной JWT. Авторизация выполняется через одноразовый
authorization code:

1. Браузер открывает `/api/auth/start` на CustDev.
2. CustDev перенаправляет его на `/auth/sso/custdev/authorize` основного Pitchy.
3. Основной Pitchy проверяет свою HttpOnly-сессию и возвращает одноразовый code.
4. CustDev обменивает code по mTLS/HMAC-защищённому server-to-server запросу.
5. CustDev создаёт собственную `__Host-custdev_session` cookie.

## Обязательные production-переменные

В обоих сервисах должны быть настроены одинаковые, но отдельные параметры:

```dotenv
CUSTDEV_SSO_CLIENT_ID=custdev
CUSTDEV_SSO_REDIRECT_URI=https://custdev.pitchy.pro/api/auth/callback
CUSTDEV_SSO_SERVICE_SECRET=<отдельный случайный секрет не менее 32 символов>
CUSTDEV_SESSION_SECRET=<отдельный случайный секрет не менее 32 символов>
```

`CUSTDEV_SSO_SERVICE_SECRET` не является `APP_SECRET_KEY` и не должен
попадать в git, логи или браузер. В production `CUSTDEV_SSO_MODE=dual` можно
использовать только как переходный режим. После проверки нового flow нужно
переключить на `code_exchange`, чтобы старый raw-cookie fallback перестал
работать.

Workflow CustDev читает только `CUSTDEV_SSO_SERVICE_SECRET` из effective
`/opt/ai-startup/.env.runtime`. Если основной Pitchy использует Lockbox, эта
строка должна быть разрешена туда через
`LOCKBOX_CUSTDEV_SSO_SERVICE_SECRET_SECRET_ID`; исходный `.env` целиком между
сервисами не копируется.

## Переключение основной cookie

После проверки SSO включить на основном Pitchy:

```dotenv
AUTH_COOKIE_HOST_ONLY=true
ACCESS_TOKEN_COOKIE_NAME=__Host-pitchy_session
```

Старый `access_token; Domain=.pitchy.pro` принимается только для миграции и
удаляется после выпуска host-only cookie. CustDev после перехода должен
игнорировать `access_token` полностью.

## Проверка

- авторизованный пользователь открывает CustDev без повторного логина;
- callback проверяет `state` и PKCE S256;
- повторное использование code отклоняется;
- exchange и introspection требуют service authentication;
- основной JWT не передаётся в CustDev и не появляется в логах;
- logout и блокировка пользователя закрывают grant через introspection;
- при истечении короткого grace period недоступность основного Pitchy закрывает
  CustDev-сессию.

До переключения `code_exchange` аварийным режимом остаётся только временный
`dual`; `ALLOW_UNVERIFIED_SESSION` включать нельзя.

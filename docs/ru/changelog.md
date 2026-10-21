# История изменений

## 0.9 — изменения относительно 0.8.5

### Комментарии каналов

- Добавлены high-level операции отправки, загрузки, получения, изменения и удаления комментариев к постам каналов.
- Добавлены реакции, подписки, счётчики, блокировка авторов, удаление комментариев пользователя и включение/выключение комментариев канала.

[//]: # (- `fetch_comments&#40;..., get_chat=True&#41;` может вернуть bound-объект `Chat` вместе с сообщениями или ID.)
- Добавлены доменные модели `CommentsInfo`, `CommentsInfoUpdate` и bound-метод `Chat.set_comments()`.

### Сообщения

- `send_message()`, `Message.answer()` и `Message.reply()` принимают `send_at`: абсолютный `datetime`, относительный `timedelta` или Unix timestamp в секундах.
- Отложенную историю можно запросить через `item_type="DELAYED"`.

### Версии клиента и Android fingerprints

- Добавлены `VersionApi` / `VersionCatalog`, встроенный каталог APK fingerprints и объединение с удалённым каталогом.
- Добавлены настройки `app_version`, `app_fingerprint`, `version_api` (alias `catalog`) и `strict_fingerprint_pair`.
- Добавлены `MaxApi.app_version`, `get_available_app_versions()`, `set_app_version()` и `set_random_app_version()`; смена версии во время работы может автоматически переподключить клиент.
- Неизвестная Android-версия может работать без fingerprint, если не включена строгая пара.
- Добавлена автоматическая смена версии после ответа unsupported client; управляется `autochange_app_version_if_current_unsupported`.

### Lifecycle и устойчивость

- Добавлены `DisconnectEvent`, `UnsupportedClientVersionEvent` и observers `Router.disconnect`, `Router.unsupported_client_version`.
- `MaxApi(dispatcher=...)` может загрузить lifecycle listeners до подключения, поэтому видны события во время инициализации. `Dispatcher.start_polling()` также автоматически устанавливает и снимает listeners.
- Добавлены директивы `reconnect`, `reconnect_delay`, `relogin`.
- Добавлены независимые circuit breakers для transport/API failures с cooldown, half-open probe, ростом recovery delay и режимом ожидания либо fail-fast.
- Усилена защита cancellation, CID, retries, reconnect и relogin от race conditions.

### Dispatcher и сырые ответы

- Добавлен `RawUpdateMode`: стандартный `TRANSLATED_ONLY` сохраняет прежнее поведение, а `ALL_RESPONSES` передаёт protocol errors и ошибки перевода во внешние update middleware.
- При ошибке перевода в middleware data добавляется `UpdateTranslationFailure`.

### Поставка и совместимость

- Добавлены CI workflows для tests, quality, package build и документации.
- В socket transport добавлен необходимый российский trust certificate; устаревшие token-file utilities удалены.

## 0.8.5 — изменения относительно 0.8

### Жизненный цикл клиента

- Создание клиента и подключение теперь можно разделить через `ExtraConfig(auto_connect_after_init=False)` и явный `await api.connect()`.
- Добавлены `request_shutdown()`, `shutdown_requested`, `wait_for_shutdown()`, `wait_until_ready()` и идемпотентный `stop()`.
- Graceful shutdown останавливает polling и mapper, ждёт активные задачи dispatcher, записывает очередь изменений сессии и закрывает storage.
- Ошибка отдельного update больше не завершает весь polling loop.

### Конфигурация и backend-стек

- Добавлены `ExtraConfig`, конфигурации отдельных слоёв и Smart Init: по `DeviceType` все неуказанные слои заполняются совместимым preset, причём аргументы конструктора приоритетнее `ExtraConfig`, а `ExtraConfig` приоритетнее стандартов preset.
- Добавлены `DeviceType` и типизированные реестры транспорта, encoding, протокола и маппера.
- Encoding выделен в отдельный слой: Web использует `JsonEncoding`, Desktop/Android — `MsgPackDictEncoding`; старый socket-envelope adapter удалён.
- Добавлены директивы `auto_connect_after_init` и `restore_user_agent_from_session`.
- Добавлены user-agent конфигурации Web, Desktop и Android и восстановление fingerprint из сессии.
- Добавлены настройки таймаутов, telemetry, proxy, endpoint, размера WebSocket frame, регистрации и sync overrides.

### Сессии и авторизация

- Добавлены асинхронное SQLite-хранилище сессий и заменяемый контракт `BaseSessionStorage`.
- Токен, телефон, устройство, user agent и sync state сохраняются и восстанавливаются.
- Добавлены `AuthInteractor`, `TerminalAuthInteractor` и `AuthCallbacks` для QR, SMS и интерактивного 2FA.
- Добавлены mapper hooks `start_auth_flow()` / `end_auth_flow()` и generic `AuthFlow` для middleware.

### Dispatcher и события

- `MaxApi(dispatcher=...)` может заранее извлечь lifecycle-listeners для событий во время авторизации. Это не привязывает dispatcher к клиенту: один dispatcher можно передать нескольким `MaxApi`.
- Добавлена ограниченная параллельная обработка через `concurrent_task_dispatch` и `concurrent_task_count`.
- Добавлен параметр handler `soft_propagate` (по умолчанию `False`) для управления строгостью dependency injection. При включении параметр получает `None` вместо `AnnotationError` и при отсутствии аннотации, и когда для его аннотации нет значения в DI/workflow-контексте. Параметр не передаёт update следующему handler.
- Данные зависимостей, возвращённые фильтрами, сохраняются при проверке handlers.
- Добавлены модели и observers `MessageReadEvent`, `TypingEvent`, `PresenceEvent`, `MessageDeleteEvent`.

### Модели и методы

- История чата умеет получать связанный чат и привязывать возвращаемые объекты к клиенту.
- Исправлены bound history и несколько lifecycle/error paths.
- Ошибки транспорта маппера и отмена запросов стали обрабатываться явнее.

Подробнее: [конфигурация](guide/configuration.md), [backend-слои](guide/backends.md), [методы и mapper](guide/methods.md).

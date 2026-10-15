# История изменений

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

- Добавлена ограниченная параллельная обработка через `concurrent_task_dispatch` и `concurrent_task_count`.
- Добавлен параметр handler `soft_propagate` (по умолчанию `False`) для управления строгостью dependency injection. При включении параметр получает `None` вместо `AnnotationError` и при отсутствии аннотации, и когда для его аннотации нет значения в DI/workflow-контексте. Параметр не передаёт update следующему handler.
- Данные зависимостей, возвращённые фильтрами, сохраняются при проверке handlers.
- Добавлены модели и observers `MessageReadEvent`, `TypingEvent`, `PresenceEvent`, `MessageDeleteEvent`.

### Модели и методы

- История чата умеет получать связанный чат и привязывать возвращаемые объекты к клиенту.
- Исправлены bound history и несколько lifecycle/error paths.
- Ошибки транспорта маппера и отмена запросов стали обрабатываться явнее.

Подробнее: [конфигурация](guide/configuration.md), [backend-слои](guide/backends.md), [методы и mapper](guide/methods.md).

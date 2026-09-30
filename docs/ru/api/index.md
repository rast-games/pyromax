# Справочник API

Страницы справочника генерируются из Python-сигнатур и Sphinx-docstring’ов Pyromax 0.8.5.

## Стабильная поверхность приложения

- `pyromax.MaxApi`, `pyromax.Dispatcher`, `pyromax.Router`, `pyromax.F`.
- Публичные модели из `pyromax.models`.
- Фильтры из `pyromax.filters`.
- FSM context, states, strategy и storage interfaces из `pyromax.fsm`.

Transport, protocol, mapping, payload и immutable-method modules относятся к расширению или внутренней реализации. Если приложение импортирует их напрямую, фиксируйте minor-версию Pyromax.

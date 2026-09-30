# API reference

The reference pages are generated from the Python signatures and Sphinx-style docstrings shipped with Pyromax 0.8.5.

## Stable application surface

- `pyromax.MaxApi`, `pyromax.Dispatcher`, `pyromax.Router`, and `pyromax.F`.
- Public models from `pyromax.models`.
- Filters from `pyromax.filters`.
- FSM context, states, strategies, and storage interfaces from `pyromax.fsm`.

Transport, protocol, mapping, payload, and immutable-method modules are extension or implementation layers. Pin the Pyromax minor version if your application imports those internals directly.

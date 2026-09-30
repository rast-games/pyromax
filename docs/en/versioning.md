# Documentation versioning

The documentation starts at **0.8** and uses `mike` to publish multiple MkDocs builds to the `gh-pages` branch. The current source tree documents **0.8.5**. Both English and Russian are built together for every version.

## Preview locally

```bash
uv sync --group dev
uv run mkdocs serve
```

## Publish or update 0.8.5

```bash
uv run mike deploy --push --update-aliases 0.8.5 latest
uv run mike set-default --push latest
```

## Publish a later release

Update documentation together with the source release, then deploy the new version while retaining previous snapshots:

```bash
uv run mike deploy --push --update-aliases 0.9 latest
```

Running `mike deploy` again with the same version replaces that version's generated snapshot. Never edit generated files on `gh-pages` manually; edit `docs/` on the source branch and deploy again.

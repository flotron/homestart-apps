# HomeStart Apps

Official declarative application catalog for [HomeStart](https://github.com/flotron/homestart).

Applications are described with a small manifest and a Docker Compose template. HomeStart downloads the generated catalog, validates it, caches the last valid copy, asks the user for the declared inputs, and creates the Compose project on the server.

## Repository layout

```text
apps/<app-id>/manifest.yaml
apps/<app-id>/compose.yaml
schema/catalog.schema.json
scripts/build_catalog.py
dist/catalog.json
```

`dist/catalog.json` is the only file consumed by HomeStart at runtime. The source files remain separated so additions and reviews stay easy to understand.

## Add an application

1. Copy one of the existing folders under `apps/`.
2. Give it a unique lowercase `id`.
3. Declare every user-editable value in `inputs`.
4. Use `{{input_id}}` placeholders in `compose.yaml`.
5. Run:

   ```bash
   python3 scripts/build_catalog.py --check
   ```

Templates must not depend on a particular HomeStart server. Use `{{homestart_data}}` for the default application-data root and `{{server_timezone}}` for the server time zone.

## Catalog contract

- `schema_version` changes only for incompatible format changes.
- HomeStart substitutes only declared placeholders and its two reserved values.
- Compose projects are labeled as managed by HomeStart.
- The client never supplies an image or Compose definition for catalog installs; HomeStart uses the validated catalog copy.
- If the remote catalog cannot be reached, HomeStart uses its cached copy and finally its built-in recommendations.

## License

MIT

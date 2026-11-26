# index.json

Built from `main` by the [Index workflow](../.github/workflows/index.yml) and published with
GitHub Pages:

| File | What it is |
| --- | --- |
| `https://tangency-labs.github.io/solidcraft-parts/index.json` | The index. |
| `https://tangency-labs.github.io/solidcraft-parts/index.json.sha256` | Its SHA-256, in `sha256sum` format. |
| `https://tangency-labs.github.io/solidcraft-parts/index-with-examples.json` | The same plus example entries, for testing clients. |
| `https://tangency-labs.github.io/solidcraft-parts/schema/library.schema.json` | The manifest schema. |
| `https://tangency-labs.github.io/solidcraft-parts/index.json.sig` | Reserved for the workshop's signature (not published yet). |

```json
{
  "index_version": 1,
  "generated_at": "2026-11-26T03:00:00Z",
  "source": { "repo": "tangency-labs/solidcraft-parts", "commit": "<40 hex digits>" },
  "libraries": [
    {
      "id": "jane-doe.aluminium-extrusions",
      "name": "Aluminium extrusions",
      "publisher": "jane-doe",
      "repo": "jane-doe/solidcraft-extrusions",
      "release": { "tag": "v1.2.0", "asset": "aluminium-extrusions-1.2.0.zip", "sha256": "<64 hex digits>" },
      "format": "folder",
      "format_version": 1,
      "min_solidcraft": "0.49.1",
      "license": "CC-BY-4.0",
      "description": "20 and 30 series T-slot profiles, brackets and nuts.",
      "tags": ["extrusions", "t-slot"],
      "homepage": "https://github.com/jane-doe/solidcraft-extrusions",
      "tier": "unverified",
      "download_url": "https://github.com/jane-doe/solidcraft-extrusions/releases/download/v1.2.0/aluminium-extrusions-1.2.0.zip",
      "manifest": "libraries/jane-doe/aluminium-extrusions.json"
    }
  ]
}
```

- `index_version` changes only when a client would read the file wrongly. Clients refuse a
  version they don't know and keep their last good copy.
- `generated_at` is the time (UTC) of the commit the index was built from, so the same commit always
  gives the same file.
- `libraries` is sorted by `id`. Each entry carries the manifest's fields (see
  [manifest.md](manifest.md)), with `tags` always present (maybe empty) and `homepage` defaulting
  to the repository, plus:
  - `download_url`: the release asset's URL;
  - `manifest`: the manifest's path in this repository.
  `release.commit` and `release.size` appear when the manifest gives them. `example: true`
  appears only in `index-with-examples.json`.
- New fields may be added within a version; clients ignore fields they don't know.

## Reading it

- Download `download_url` and check its SHA-256 against `release.sha256` before using it. A
  mismatch is a failed download, never a warning.
- Skip entries whose `format` or `format_version` you don't support, and entries whose
  `min_solidcraft` is newer than the running app (show them as needing an update).
- Show `tier` as the same badge everywhere: Official, Community, Unverified.
- Unpack the zip into the library folder; never run anything from it.

## Signing

The index will be signed by the workshop. The plan is a detached signature published next to it
as `index.json.sig`; the Index workflow has a step for it that is off until the signing is set up.
Until then, clients treat the index as unsigned and rely on HTTPS and each asset's SHA-256.

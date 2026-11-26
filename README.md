# SolidCraft parts index

The community list of parts libraries for [SolidCraft](https://solidcraft.io). Each library
lives in its author's own GitHub repository; this repository only lists them, one small manifest
per library, so SolidCraft and the SolidCraft workshop (workshop.solidcraft.io) can find
them.

The index is built from `main` and published at:

```
https://tangency-labs.github.io/solidcraft-parts/index.json
```

Its layout is in [docs/index-format.md](docs/index-format.md).

## Add your library

1. **Publish a release.** In your library's public GitHub repository, make a release and attach
   a `.zip` of your parts folder: the designs (`.sc`), STEP and mesh files, in subfolders if you
   like, exactly as the Parts Library panel in SolidCraft shows them. See
   [docs/library-format.md](docs/library-format.md).

2. **Write a manifest.** Fork this repository and add `libraries/<your GitHub account>/<library>.json`
   (all lower case). Copy [the example](libraries/tangency-labs/example-cube.json), drop its
   `example` line, and fill in your repository, the release tag, the asset's name and its SHA-256:

   ```sh
   sha256sum my-library-1.0.0.zip        # Linux
   shasum -a 256 my-library-1.0.0.zip    # macOS
   Get-FileHash my-library-1.0.0.zip     # Windows PowerShell
   ```

   Set `"tier": "unverified"`. The fields are described in
   [docs/manifest.md](docs/manifest.md) and checked against
   [schema/library.schema.json](schema/library.schema.json).

3. **Open a pull request.** CI checks the manifest, finds your release, downloads the asset and
   checks its SHA-256. When it is green I review it and merge it, and your library is in the next
   index.

To ship a new version later, make a new release and open a pull request that changes `release`
in your manifest.

## Tiers

| Tier | Meaning |
| --- | --- |
| Unverified | Listed and machine-checked: the manifest, the release and its hash. Every new library starts here. |
| Community | Reviewed by the SolidCraft maintainers. |
| Official | Published by Tangency Labs. |

Only maintainers change a library's tier. SolidCraft and the workshop show the same badge.

## Check a manifest yourself

```sh
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/check.py manifests --network libraries/<you>/<library>.json
```

## Licence

The index (manifests, schema, scripts and docs) is under the [MIT licence](LICENSE). Each library
keeps its own licence, given in its manifest.

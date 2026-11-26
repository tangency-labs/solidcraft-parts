# Library manifest

One JSON file per library at `libraries/<publisher>/<library>.json`, checked against
[schema/library.schema.json](../schema/library.schema.json). Names are lower case: letters,
digits and hyphens.

```json
{
  "$schema": "../../schema/library.schema.json",
  "manifest_version": 1,
  "id": "jane-doe.aluminium-extrusions",
  "name": "Aluminium extrusions",
  "publisher": "jane-doe",
  "repo": "jane-doe/solidcraft-extrusions",
  "release": {
    "tag": "v1.2.0",
    "asset": "aluminium-extrusions-1.2.0.zip",
    "sha256": "<64 hex digits>"
  },
  "format": "folder",
  "format_version": 1,
  "min_solidcraft": "0.49.1",
  "license": "CC-BY-4.0",
  "description": "20 and 30 series T-slot profiles, brackets and nuts, modelled from published dimensions.",
  "tags": ["extrusions", "t-slot"],
  "homepage": "https://github.com/jane-doe/solidcraft-extrusions",
  "tier": "unverified"
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `$schema` | no | Lets editors check the file as you type. |
| `manifest_version` | yes | Always `1`. |
| `id` | yes | `<publisher>.<library>`: the folder name, a dot, the file name without `.json`. Never changes once listed. |
| `name` | yes | Shown in SolidCraft and on the workshop, 2 to 80 characters. |
| `publisher` | yes | The GitHub account (user or organisation) that owns `repo`, lower case. Same as the folder. |
| `repo` | yes | The library's public GitHub repository, `owner/name`. |
| `release.tag` | yes | The tag of a published release in `repo`. |
| `release.asset` | yes | The `.zip` attached to that release. |
| `release.sha256` | yes | The asset's SHA-256, lower-case hex. Clients refuse a download that doesn't match it. |
| `release.commit` | no | The full commit SHA the tag points to. When given, CI checks the tag hasn't moved. |
| `release.size` | no | The asset's size in bytes. When given, CI checks it. |
| `format` | yes | What the asset holds. `folder` is the only format so far: see [library-format.md](library-format.md). |
| `format_version` | yes | `1`. |
| `min_solidcraft` | yes | The oldest SolidCraft release the library works in, `major.minor.patch`. The Parts Library panel first shipped in 0.49.1. |
| `license` | yes | An [SPDX licence id](https://spdx.org/licenses/) or expression, such as `MIT`, `CC-BY-4.0` or `CC-BY-SA-4.0 OR MIT`. |
| `description` | yes | One or two sentences, 10 to 500 characters. |
| `tags` | no | Up to 12 lower-case tags. |
| `homepage` | no | An `https` page about the library. Defaults to the repository. |
| `tier` | yes | `unverified` in every pull request. Maintainers set `community` or `official`. |
| `example` | no | Only on the example manifest. Example entries are left out of `index.json`. |

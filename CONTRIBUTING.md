# Contributing to the SolidCraft parts index

Thanks for sharing your parts. This page covers what gets listed and how a pull request is
reviewed. How to add a library is in the [README](README.md).

## What a pull request may change

- **Your own folder only.** A pull request may add, change or remove manifests in
  `libraries/<your GitHub account>/`, or in the folder of an organisation you are a **public**
  member of (make your membership public in the organisation's People page if CI says otherwise).
  Changes to anything else (the schema, scripts, workflows, docs) are made by maintainers; if you
  think one is needed, open an issue.
- **The publisher owns the repository.** A manifest's `publisher` is the GitHub account that owns
  its `repo`, so you list your own libraries, not someone else's.
- **Ids don't change.** Once a library is listed its `id` stays the same. To rename it, change
  `name`.
- **Tier is `"unverified"`.** Maintainers set `community` or `official`. An update keeps the tier
  the library already had.

## What CI checks

Every pull request runs the [Check workflow](.github/workflows/check.yml):

- each changed manifest matches [the schema](schema/library.schema.json);
- its path matches its `publisher` and `id`, and no two libraries share an id;
- `license` is an SPDX licence id or expression;
- the pull request touches only folders its author may publish for, and keeps to the tier rule;
- `repo` is a public repository owned by the publisher, `release.tag` is a published release
  there, `release.asset` is attached to it, and the asset's SHA-256 matches;
- the asset is a zip that holds at least one part and no programs or scripts.

CI runs on `pull_request` with a read-only token and no secrets. It never runs anything from your
repository: it downloads the asset, hashes it and reads the zip's file list without unpacking it.

## Review rules

I review every pull request before it merges. Most of the review is about where the parts came
from.

- **Clean room.** List parts you modelled yourself, from dimensions in public standards, from your
  own measurements, or from a datasheet's published dimensions. Say in your repository how the
  parts were made.
- **No copied vendor CAD without a licence.** Many manufacturers offer CAD downloads under terms
  that forbid passing the files on. Don't repackage those files unless the vendor's licence allows
  it (link it in your repository), or the vendor publishes the library themselves.
- **Brand libraries are welcome as community entries.** A library for one maker's parts, such as
  a range of inserts, extrusions or connectors, is a good fit here: it updates on its own schedule
  without waiting for a SolidCraft release. SolidCraft itself keeps only standards-based parts
  (ISO and ANSI screws, nuts, washers and so on). A vendor that publishes its own library can ask
  for it to be listed under its own account.
- **No trademarks used to mislead.** Name a library for what is in it. Don't present a library as
  a manufacturer's official one unless the manufacturer publishes it.
- **Parts only.** A parts library holds designs, STEP and mesh files, with pictures and notes if
  you like. Code belongs in a SolidCraft plugin, which has its own review.
- **Licence.** Choose a licence that lets people use the parts in their own designs, such as
  MIT, CC-BY-4.0 or CC0-1.0, and put the licence file in your repository.

A listed library can be removed if its release disappears, its hash stops matching, or it breaks
these rules. If something listed here is yours and shouldn't be, open an issue and I'll take it
down.

## Maintainers

Maintainers are listed in [.github/maintainers.txt](.github/maintainers.txt). Their pull requests
may change any file and set tiers. CI reads that file from `main`, never from the pull request.

# Library format: `folder`, version 1

A library's release asset is a `.zip` file. Unzipped, it is a folder the SolidCraft **Parts
Library** panel can show as it is: choose the folder in the panel and the parts appear.

- **Parts.** SolidCraft designs (`.sc`), STEP files (`.step`, `.stp`) and meshes (`.stl`, `.3mf`,
  `.obj`, `.glb`, `.gltf`). A design drags in as a linked component; a STEP or mesh file is
  imported.
- **Subfolders** group parts; the panel opens them in place. Keep the whole library in one folder
  at the top of the zip, so it unpacks to one folder.
- **Alongside the parts** you may keep pictures, a `README`, a `LICENSE` and notes. The panel
  doesn't show them. Files whose names start with `.` or `~` are hidden.
- **Not allowed:** programs and scripts (`.exe`, `.dll`, `.so`, `.sh`, `.py`, `.js`, `.wasm` and
  the like), symbolic links, absolute paths and `..` in paths. Code belongs in a SolidCraft plugin.
- **Size:** up to 2 GiB, GitHub's limit for a release asset. Smaller is kinder to everyone.

Example layout:

```
aluminium-extrusions-1.2.0.zip
└── Aluminium extrusions/
    ├── README.md
    ├── LICENSE
    ├── 20 series/
    │   ├── 2020 profile.sc
    │   └── 2020 corner bracket.step
    └── 30 series/
        └── 3030 profile.sc
```

A later format version may add a metadata file inside the zip (part names, thumbnails,
parameters). Until then, the file names are the part names.

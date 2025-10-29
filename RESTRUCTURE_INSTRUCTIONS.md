# Repository Restructuring Required

Home Assistant requires addon repositories to have this structure:

```
repository-root/
├── repository.json          (at root)
└── melcloudhome-bridge/     (addon folder with slug name)
    ├── config.yaml
    ├── Dockerfile
    ├── run.sh
    ├── README.md
    ├── CHANGELOG.md
    ├── icon.png (optional)
    └── app/
        └── ... (your Python code)
```

## Steps to fix:

1. Create a new directory called `melcloudhome-bridge/` (matching your slug)
2. Move these files INTO that directory:
   - config.yaml
   - Dockerfile
   - run.sh
   - README.md
   - CHANGELOG.md
   - app/
   - requirements.txt
   
3. Keep at root level:
   - repository.json (update it to list the addon)
   
4. Update repository.json to reference the addon

## Alternative: Use build.yaml

If you want to keep the current structure, you can use build.yaml to define where your addon lives, but the standard approach is to use subdirectories.

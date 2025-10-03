#!/bin/bash

# Masuk ke folder project
cd ~/lootgames

# Commit semua perubahan
git add .
git commit -m "Auto backup $(date +'%Y-%m-%d_%H-%M-%S')" 2>/dev/null

# Push ke GitHub
git push origin main

# Tarik update dari GitHub
git pull origin main


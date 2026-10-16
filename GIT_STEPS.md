# Git steps (run in the VS Code terminal, inside your cloned repo folder)

```powershell
# 1. Make sure you start from an up-to-date main
git checkout main
git pull

# 2. Create and switch to the new branch
git checkout -b cleanup/restructure-sql

# 3. Remove the old/duplicate files from the repo
git rm "CREATE TABLE IF NOT EXISTS SALES_ITEMS(.sql"
git rm "Pharmacy Local.session.sql" "PharmacySalesAndInventory Local.session.sql"
git rm schema.sql seed.sql .vscode/setup.sql
git rm --cached .vscode/settings.json        # stop tracking the file with the password

# 4. Copy the new files in (sql/, docs/, setup.bat, README.md, .gitignore,
#    .vscode/settings.example.json) - overwrite README.md when asked.

# 5. Stage, commit, push
git add .
git status                                   # check: settings.json must NOT be listed
git commit -m "Restructure repo: numbered SQL files, fixed schema, triggers, roles, tests"
git push -u origin cleanup/restructure-sql
```
Then open a Pull Request on GitHub, have a teammate review, and merge into main.

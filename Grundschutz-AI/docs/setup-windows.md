# Windows 11 workstation setup — Sprint 0

Run in **PowerShell** as the regular user. `winget` may request elevation or confirmation during installation. Do not run scripts copied from unverified sources.

## 1. Install only core tools

```powershell
winget install --id Git.Git -e
winget install --id Microsoft.VisualStudioCode -e
winget install --id Python.Python.3.12 -e
```

Close and reopen PowerShell and VS Code so PATH updates are visible. Existing installations may be retained if supported.

## 2. Verify tools

```powershell
git --version
py -3.12 --version
code --version
Get-CimInstance Win32_Processor | Select-Object Name
Get-PSDrive -Name C
```

For safer verification without changing files run `scripts/check_environment.ps1` (script reports status only).

## 3. Codex in VS Code (recommended path)

Open VS Code > Extensions, install **Codex / OpenAI** from the official publisher, open Codex sidebar, then sign in. See https://learn.chatgpt.com/docs/codex/ide . Keep Windows-native sandbox/approval protections enabled. Codex does not need Ollama to write project code.

**Alternative:** Codex CLI can be installed via official OpenAI instructions: https://learn.chatgpt.com/docs/codex/cli . The VS Code extension alone is sufficient for Sprint 0.

## 4. Create local repo

```powershell
# After extracting Sprint0 ZIP to your chosen folder:
cd "$HOME\Projects\Grundschutz-AI"
git init
git add README.md GOALS.md AGENTS.md PLANS.md .gitignore docs tasks scripts
git commit -m "chore: establish Grundschutz AI sprint 0 baseline"
```

`git commit` may require configuring a local author identity with `git config user.name` / `git config user.email`; do not use confidential data as author details.

## 5. Open and test Codex

```powershell
code .
git status
```

In Codex choose a mode that asks permission before operations, then paste `tasks/CODEX_TASK_001.md` as the first task. Do not load company files.

## 6. Optional read-only PowerShell check

```powershell
powershell -NoProfile -File .\scripts\check_environment.ps1
```

## Not in Sprint 0

Do **not** install Ollama, large AI models, Docker, WSL, database servers, or extra Python packages yet.

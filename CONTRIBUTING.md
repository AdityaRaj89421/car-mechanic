# Contributing to AI Car Mechanic

## ⚠️ Credential & Secret Hygiene — MANDATORY RULES

These rules apply to every contributor, every commit, and every document in this repo.

### The Golden Rule

> **Real credential values are NEVER written into any file that is tracked by git,**  
> **except `.env` and `.env.local` — which are gitignored and never committed.**

| File type | Real key allowed? |
|---|---|
| `backend/.env` | ✅ Yes — gitignored |
| `frontend/.env.local` | ✅ Yes — gitignored |
| `*.py`, `*.ts`, `*.tsx` | ❌ NO |
| `README.md`, `CONTRIBUTING.md`, `*.md` docs | ❌ NO |
| Test files (`test_*.py`, `*.test.ts`) | ❌ NO |
| CI / GitHub Actions `.yml` files | ❌ NO (use repo secrets) |
| Comments in any source file | ❌ NO |

### Approved placeholders in non-`.env` files

When a credential placeholder is needed in documentation, examples, or CI config, use **only** these forms:

```
GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>
DJANGO_SECRET_KEY=<50-char random string>
GEMINI_API_KEY=<REDACTED>
```

Never use a real key value, even as an "example."

---

### What to do if a key is accidentally committed

1. **Rotate the key immediately** in the provider's console (Google AI Studio, AWS IAM, etc.).
   The compromised key should be treated as fully public the moment it touches git history.

2. **Remove it from history** using `git filter-repo` or BFG Repo Cleaner:
   ```bash
   pip install git-filter-repo
   git filter-repo --replace-text <(echo 'OLD_KEY_VALUE==>REDACTED')
   git push --force --all
   ```
   > ⚠️ Force-push rewrites history for all collaborators. Coordinate before doing this.

3. **Audit all other secrets** — if one key leaked, others may have too.

---

### Environment variable setup for local development

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env — fill in your real GEMINI_API_KEY, DJANGO_SECRET_KEY

# Frontend
cp frontend/.env.local.example frontend/.env.local
# Edit frontend/.env.local — set NEXT_PUBLIC_API_BASE_URL
```

These files are in `.gitignore` and will never be committed.

---

### Checklist before every commit

- [ ] `git diff --cached | grep -E "AIzaSy|AKIA|sk-|ghp_"` returns nothing
- [ ] No real API keys appear in any `.py`, `.ts`, `.tsx`, `.md`, or `.yml` file
- [ ] Test files use `unittest.mock.patch` for API calls, not real credentials
- [ ] `npm run lint` passes (frontend)
- [ ] `python manage.py check` passes (backend)
- [ ] Commit message follows Conventional Commits (`feat:`, `fix:`, `test:`, etc.)

# Ship Skill

Commit and push changes after verification passes.

## Usage
Run `/ship` after `/verify` passes.

## Pre-Ship Checklist

### 1. Verify First
```bash
# Must have run /verify and all checks passed
```

### 2. Check What's Staged
```bash
git status
git diff --cached --stat
```

### 3. Review Changes
```bash
git diff --cached
```

## Commit Process

### 1. Stage Changes
```bash
# Stage specific files (preferred)
git add [specific files]

# Or stage all (use sparingly)
git add -A
```

### 2. Commit with Conventional Format
```bash
git commit -m "type(scope): description"
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `docs`: Documentation
- `test`: Tests
- `chore`: Maintenance

**Examples:**
```bash
git commit -m "feat(detection): add hallucination detector"
git commit -m "fix(proxy): handle null response from LLM"
git commit -m "refactor(models): split incident model into package"
```

### 3. Push to Remote
```bash
git push origin main
```

## Post-Ship

### Verify Push Succeeded
```bash
git log --oneline -1
git status
```

### Check Remote
```bash
git fetch origin
git log origin/main --oneline -3
```

## Output Format
```
## Ship Results - [TIMESTAMP]

### Committed
- Hash: [commit hash]
- Message: [commit message]
- Files: [count] files changed

### Pushed
- Branch: [branch name]
- Remote: origin

### Status: SHIPPED
```

## Rules

1. **Never** commit without passing `/verify`
2. **Never** add `Co-Authored-By` lines
3. **Always** use conventional commit format
4. **Always** push after commit (every session ends with push)
5. **Never** force push to main

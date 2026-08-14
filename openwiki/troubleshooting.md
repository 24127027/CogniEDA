---
type: Troubleshooting Guide
title: CogniEDA Troubleshooting and FAQ
description: Common issues, solutions, error messages, and frequently asked questions.
tags: [troubleshooting, faq, errors, support]
---

# Troubleshooting and FAQ

## Installation Issues

### Issue: "cognieda command not found"

**Cause**: Tool not installed or shell not updated

**Solution**:
```powershell
# Reinstall
uv tool install --editable .

# Update shell environment
uv tool update-shell

# Open new PowerShell window and try again
cognieda --help
```

### Issue: "ModuleNotFoundError: No module named 'cognieda'"

**Cause**: Dependencies not installed

**Solution**:
```powershell
cd /path/to/CogniEDA
uv sync
uv tool install --editable .
```

### Issue: Python version error

**Cause**: Python < 3.12

**Solution**:
```powershell
python --version  # Check version
# Install Python 3.12+ from python.org or use pyenv
uv sync
```

---

## Configuration Issues

### Issue: "API key not found" or "Invalid API key"

**Cause**: `MODEL_API_KEY` not set in `.env`

**Solution**:
```powershell
# Create .env if not present
copy .env.example .env

# Edit .env and add your API key
# For Google:
MODEL_API_KEY=AIzaSy...

# For OpenAI:
MODEL_API_KEY=sk-...

# For Anthropic:
MODEL_API_KEY=sk-ant-...
```

### Issue: "Provider not supported: custom_provider"

**Cause**: Invalid provider specified

**Solution**: Check `.cognieda/project.toml`:
```toml
# Valid options:
model.provider = "google"      # Default
model.provider = "openai"      # OpenAI GPT
model.provider = "anthropic"   # Claude
```

### Issue: "COGNIEDA_DB_URL invalid"

**Cause**: Malformed database URL

**Solution**: Check environment or workspace config:
```powershell
# SQLite (default)
$env:COGNIEDA_DB_URL = "sqlite:///path/to/db.db"

# PostgreSQL
$env:COGNIEDA_DB_URL = "postgresql://user:pass@localhost/cognieda"

# Leave unset to use workspace-local SQLite
Remove-Item Env:\COGNIEDA_DB_URL
```

---

## Runtime Issues

### Issue: "Database is locked"

**Cause**: Multiple processes accessing same SQLite file

**Solution**:
```powershell
# Option 1: Kill other cognieda processes
Get-Process python | Stop-Process  # (careful!)

# Option 2: Delete local database and restart
Remove-Item .cognieda\.cognieda.db
cognieda

# Option 3: Use external database
# Set COGNIEDA_DB_URL to PostgreSQL or similar
```

### Issue: "Session file not found" or "Cannot resume frame"

**Cause**: SessionFrame ID doesn't exist

**Solution**:
```
> show frames          # List available SessionFrames
> resume frame-007    # Use valid ID
```

### Issue: "Objective not found" or "Evidence invalid"

**Cause**: Database desynchronized or workspace changed

**Solution**:
```
> show objectives     # List what exists
> show evidence       # Check evidence state
# If not found, may have switched workspaces
cognieda /correct/workspace/path
```

---

## Execution Issues

### Issue: "Cannot execute without approved hypotheses"

**Cause**: No hypotheses approved yet

**Solution**:
```
> hypothesize                # Generate hypotheses
> approve <id> [<id> ...]   # Approve specific ones
> execute                   # Run execution
```

### Issue: "Task execution failed" or "Analysis timed out"

**Cause**: 
- Dataset too large
- Complex computation
- Network timeout
- Out of memory

**Solution**:
```
# Check task logs
$env:COGNIEDA_LOG_LEVEL = "debug"
cognieda

# Re-run with timeout increase
# In .cognieda/project.toml:
[execution]
timeout = 600  # Increase from 300 to 600 seconds

# For large datasets:
# Filter or sample data first
> filter "sample_fraction < 0.5"  # Use 50% sample
> execute
```

### Issue: "LLM rate limit exceeded"

**Cause**: Too many requests to model provider

**Solution**:
```
# Wait and retry
# Option 1: Manual retry
> execute  # Try again after a minute

# Option 2: Use mock mode for testing
cognieda --mode mock

# Option 3: Check provider rate limits
# Google: 60 requests/minute
# OpenAI: Depends on tier
# Anthropic: Check dashboard
```

### Issue: "Out of memory" error

**Cause**: Dataset too large for available RAM

**Solution**:
```
# Sample data
> filter "ROW_NUMBER() % 100 = 0"  # Take every 100th row

# Or load in chunks (if supported by data source)
> load data.csv --chunk_size=10000

# Increase available memory (if possible)
# For Python: Adjust system memory allocation
```

---

## Data Issues

### Issue: "Data validation failed"

**Cause**: Data doesn't match schema

**Solution**:
```
> validate                    # Check what failed
# Review the validation error message

# Option 1: Fix source data
# Update data to match schema, then reload

# Option 2: Adjust schema
# .cognieda/project.toml
[validation]
strict = false  # More lenient validation

# Option 3: Clean data in-pipeline
> impute <column>             # Fill missing values
> filter "column IS NOT NULL" # Remove invalid rows
```

### Issue: "Data Profile invalid or superseded"

**Cause**: Source data changed after profiling

**Solution**:
```
# Reload and re-profile
> load data/updated_data.csv
# New DataProfile created
# Old Evidence marked as PROVISIONAL
# May need to re-run analysis
```

### Issue: "Cannot load file" or "Data format not supported"

**Cause**: File not found or unsupported format

**Solution**:
```
# Check file exists and is readable
test-path data/file.csv

# Supported formats: CSV, Parquet, JSON, Excel
# Make sure file extension matches format

# Try with full path
> load "C:\absolute\path\to\data.csv"

# Check file permissions
ls -la data/
```

---

## Hypothesis and Evidence Issues

### Issue: "Cannot evaluate hypothesis without evidence"

**Cause**: No evidence generated for hypothesis

**Solution**:
```
> approve <hypothesis-id>
> execute        # This should generate evidence
> evaluate       # Now you can evaluate
```

### Issue: "Evidence still marked PROVISIONAL after re-run"

**Cause**: Source data changed or evaluation inconclusive

**Solution**:
```
> show evidence   # Check current state
# If evidence shows PROVISIONAL:
# Either source data is uncertain
# Or analysis results aren't strong enough

# Options:
# 1. Improve data quality
# 2. Refine hypothesis
# 3. Gather more evidence
# 4. Accept uncertainty and proceed
```

### Issue: "Hypothesis evaluation confidence too low"

**Cause**: Evidence doesn't strongly support claim

**Solution**:
```
> show evaluations         # Check confidence scores
# If < 0.7 (typically):

# Option 1: Gather more evidence
> execute  # More analysis

# Option 2: Refine hypothesis
> refine <id> "More specific claim"

# Option 3: Accept as weak evidence
# Document that this is exploratory, not confirmed
```

---

## Discovery and Authority Issues

### Issue: "Cannot admit discovery - authority not granted"

**Cause**: Insufficient approval authority

**Solution**:
```
# Ensure:
# 1. Evidence exists and is valid
> show evidence

# 2. Hypothesis is evaluated
> evaluate <hypothesis>

# 3. Confidence is sufficient (typically > 0.8)
> show evaluations

# 4. Human has approval authority
# (Should be you if running locally)

# Then admit:
> admit <discovery-id>
```

### Issue: "Retraction cascaded and invalidated other discoveries"

**Cause**: Retracted discovery was used in downstream analysis

**Solution**:
```
# This is expected behavior - validity propagates
# Review dependent discoveries
> show discoveries

# Option 1: Re-evaluate with new evidence
# Re-run analysis that depended on retracted discovery

# Option 2: Retract dependent discoveries too
> retract <dependent-id>

# Option 3: Leave as PROVISIONAL
# Flag for review but don't retract
```

---

## Database Issues

### Issue: "Database corruption" or "Integrity constraint violation"

**Cause**: Incomplete transaction or software bug

**Solution**:
```powershell
# Backup current database
copy .cognieda\.cognieda.db .cognieda\.cognieda.db.backup

# Reset database
Remove-Item .cognieda\.cognieda.db

# Restart
cognieda

# If issue persists:
# Report on GitHub with:
# - Python version (python --version)
# - OS (Windows/macOS/Linux)
# - Exact steps to reproduce
```

### Issue: "Transaction timeout"

**Cause**: Long-running transaction or deadlock

**Solution**:
```
# Increase timeout in .cognieda/project.toml:
[persistence]
transaction_timeout = 30  # seconds

# Or restart cognieda to clear locks
```

---

## Performance Issues

### Issue: "Analysis very slow"

**Cause**: 
- Large dataset
- Complex computation
- Network latency
- Insufficient resources

**Solution**:
```
# Check current performance
# Enable debug logging
$env:COGNIEDA_LOG_LEVEL = "debug"

# Profile bottleneck:
# 1. Data loading: Sample data first
# 2. Analysis: Complex algorithms? Simplify or optimize
# 3. LLM calls: Batch requests
# 4. Database: Check indices

# Quick fix: Use smaller dataset
> filter "ROW_NUMBER() < 1000"  # First 1000 rows
```

### Issue: "Memory usage growing unbounded"

**Cause**: Memory leak or large data in memory

**Solution**:
```
# Restart cognieda periodically
# Explicit garbage collection not typically needed in Python

# For large datasets:
# Use streaming or chunked processing
# Sample data for exploration

# Monitor memory (outside cognieda):
# Task Manager → Performance tab
```

---

## Development/Testing Issues

### Issue: Tests fail with "fixture not found"

**Cause**: Test fixtures not properly set up

**Solution**:
```powershell
uv run pytest tests/unit/test_example.py -v
# Check fixture definitions in tests/fixtures/
```

### Issue: Type checking errors with mypy

**Cause**: Type hints or stubs missing

**Solution**:
```powershell
uv run mypy src/cognieda --show-error-codes
# Check pyproject.toml mypy configuration
# May need to install type stubs for dependencies
```

### Issue: Linting complaints about valid code

**Cause**: Ruff style rules differ from your preference

**Solution**:
```powershell
# Auto-format code to match style
uv run ruff check --fix src/cognieda

# Or customize rules in pyproject.toml
[tool.ruff]
line-length = 88
```

---

## FAQ

### Q: Can I use CogniEDA for real-time analysis?

**A**: MVP is not optimized for real-time. Better for batch analysis. Real-time support is on the roadmap.

### Q: Can I use multiple workspaces simultaneously?

**A**: Yes, but in separate cognieda processes. Each process has one active workspace.

### Q: How do I backup my research state?

**A**: Backup `.cognieda/` directory:
```powershell
copy -Recurse .cognieda .cognieda.backup
```

### Q: Can I export discoveries to CSV or JSON?

**A**: Not yet built-in, but you can query the database directly:
```python
from cognieda.infrastructure.persistence import DatabaseSession
# (Advanced - not documented yet)
```

### Q: How do I collaborate with team members?

**A**: 
- Use shared workspace directory on network drive
- Or shared database (set COGNIEDA_DB_URL)
- Use SessionFrames to coordinate context

### Q: What happens if I delete a discovered fact?

**A**: Retracting a discovery invalidates dependent work. Full audit trail preserved.

### Q: Can I run cognieda without internet?

**A**: No - LLM API calls require network. Use `--mode mock` for testing offline.

### Q: How is my data stored?

**A**: In `.cognieda/.cognieda.db` (SQLite) in your workspace. Or external database if configured. Never sent to CogniEDA servers (but sent to LLM provider).

### Q: Is CogniEDA open source?

**A**: Yes, under LICENSE in the repository.

### Q: How do I get support?

**A**: 
- Check [Troubleshooting Guide](./troubleshooting.md) (this page)
- Search [GitHub Issues](https://github.com/your-org/CogniEDA/issues)
- Ask in [GitHub Discussions](https://github.com/your-org/CogniEDA/discussions)
- Report bugs with reproduction steps

### Q: Can I contribute?

**A**: Yes! See [Development Setup](../development/setup.md) for how to get started.

### Q: What's the roadmap?

**A**: See [Current Status](../status/current-state.md) for detailed roadmap.

---

## Reporting Bugs

Please include:

1. **Reproduction steps** - Exactly what you did
2. **Expected behavior** - What you expected to happen
3. **Actual behavior** - What happened instead
4. **System info**:
   ```powershell
   python --version
   uv --version
   $PSVersionTable.PSVersion  # PowerShell version
   ```
5. **Logs**:
   ```powershell
   $env:COGNIEDA_LOG_LEVEL = "debug"
   cognieda  # Run and capture output
   ```
6. **Configuration**:
   ```
   MODEL_API_KEY=sk-***  # Redact key
   .cognieda/project.toml contents
   ```

Submit to: [GitHub Issues](https://github.com/your-org/CogniEDA/issues/new)


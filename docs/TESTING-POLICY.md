# Testing Policy

## Rule: All New Code Must Include Unit Tests

**Effective immediately.** Any pull request that adds new functionality or modifies existing behavior without unit tests will be rejected.

### What Requires Tests

✅ **Always test:**
- New API endpoints (routes)
- New database operations/queries
- New filtering, sorting, or business logic
- Bug fixes (include regression test)
- Changes to core models or utilities

⚠️ **May skip tests for:**
- Pure UI/presentation components (tested via manual verification)
- Configuration-only changes (nginx, docker-compose)
- Documentation changes
- Refactors where behavior is unchanged (refactoring tests still validate behavior)

### Minimum Coverage Guidelines

| Code Type | Minimum Coverage |
|-----------|------------------|
| API routes | Success path + all error cases (400, 404, 422, 401) |
| Filters/sorting | Happy path + edge cases (empty results, invalid params) |
| Utilities | Full coverage of all branches |
| Models | Optional (SQLAlchemy validates most issues) |

### Test Organization

```
backend/tests/
├── test_health.py              # Infrastructure
├── test_devices.py             # Device endpoints
├── test_devices_filter_sort.py # Device filtering/sorting (NEW)
├── test_errors.py              # Error endpoints
├── test_commands.py            # Command endpoints
├── test_mqtt_manager.py        # MQTT service
└── conftest.py                 # Fixtures & DB setup
```

Each test file covers **one domain** (devices, errors, commands, MQTT, etc).

### Running Tests Locally

```bash
# Run all tests
docker compose exec backend pytest tests/ -v

# Run specific file
docker compose exec backend pytest tests/test_devices.py -v

# Run specific test
docker compose exec backend pytest tests/test_devices.py::test_list_devices -v

# Run with coverage
docker compose exec backend pytest tests/ --cov=app --cov-report=term-missing
```

### Test Isolation

The test harness uses SQLAlchemy savepoints with `join_transaction_mode="create_savepoint"` to achieve true per-test isolation:

- Each test runs inside a transaction that rolls back on teardown
- `db.commit()` in route handlers becomes a SAVEPOINT, not a real commit
- Tests never affect each other, even when tests modify the same tables
- No need to clean up data between tests

### Example: Adding a New Feature

**Before:** You write the feature without tests.

**After:** You write tests first (or simultaneously):

```python
# 1. Write test in test_devices_filter_sort.py
def test_filter_by_status(client, auth_headers, test_devices):
    resp = client.get("/api/devices?online=true", headers=auth_headers)
    assert resp.status_code == 200
    assert all(d["online"] is True for d in resp.json()["devices"])

# 2. Write the feature to make the test pass
# 3. Run tests to verify

# 4. Open PR — CI runs pytest automatically
# 5. Code review includes test review
```

### CI Integration (Future)

When we set up CI/CD:

```yaml
- Run: pytest tests/ --cov=app --cov-report=xml
- Fail PR if: coverage < 80% OR any test fails
- Report coverage to PR comment
```

### Learning from This Sprint

**What we learned:**

- **Device list API**: Took 35 endpoints + 0 tests initially, then we added 29 tests
- **MQTT service**: Wrote 30 unit tests + 1 integration test
- **Filtering/sorting**: Wrote feature code first, tests second, caught bugs in tests

**Pattern:** Tests catch edge cases the developer doesn't think of. Writing tests second is better than not writing them.

### FAQ

**Q: Do I need to test the UI (React)?**

A: Not with unit tests (harder to set up). Instead:
1. Use `verify` skill to manually test in browser
2. Write integration tests if feature is complex (future work)
3. File bugs if UI behaves unexpectedly

**Q: What if a test is hard to write?**

A: That's a signal the code is too complex. Options:
1. Simplify the code (preferred)
2. Break it into smaller testable pieces
3. Ask for help in code review

**Q: Can I skip tests for "obvious" code?**

A: No. "Obvious" code often has hidden bugs (off-by-one errors, null checks, edge cases). Tests are the proof of correctness.

**Q: What coverage % should we aim for?**

A: 80%+ on new code is good. Don't optimize for coverage percentage — optimize for *meaningful* tests that catch bugs.

### Checklist for PR Authors

Before opening a PR:
- [ ] New feature has corresponding tests
- [ ] Tests cover success path
- [ ] Tests cover error cases
- [ ] All tests pass locally: `pytest tests/ -v`
- [ ] Coverage on new code: `pytest tests/ --cov=app`
- [ ] Tests are readable (good names, clear assertions)

### Checklist for Code Reviewers

When reviewing a PR:
- [ ] Changes have corresponding tests
- [ ] Tests actually test the feature (not just passing vacuously)
- [ ] Tests cover edge cases
- [ ] Tests follow existing patterns
- [ ] Tests aren't testing framework code (let SQLAlchemy/FastAPI do that)

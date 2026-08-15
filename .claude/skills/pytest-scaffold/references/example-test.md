# Worked Example

Reference style, taken from [tests/test_app.py](../../../../tests/test_app.py). Match this shape for any new test file.

```python
from src.app import create_app


def test_health_returns_ok():
    client = create_app().test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
```

Notes on the pattern:

- **Arrange** — build whatever the test needs (here, a test client). One blank line after.
- **Act** — perform the one action under test (here, the request). One blank line after.
- **Assert** — one or more assertions on the result. No blank lines between assertions.
- No comments marking the phases (`# arrange`, `# act`, `# assert`) — the blank lines alone carry the structure.
- Test function names describe the behavior, not the mechanism: `test_health_returns_ok`, not `test_get_health`.
- For a Flask route, always go through `create_app().test_client()` rather than calling the view function directly.
- For a plain function (no Flask route involved), the same three-phase shape applies, just without a test client:

```python
from src.some_module import calculate_total


def test_calculate_total_sums_positive_values():
    values = [10, 20, 30]

    result = calculate_total(values)

    assert result == 60
```

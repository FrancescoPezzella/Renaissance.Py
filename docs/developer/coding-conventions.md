# Coding conventions

This page captures conventions that are smaller in scope than an [architecture decision](architecture/adr/README.md):
naming, formatting, and other day-to-day coding habits rather than design decisions.

We follow the standard Python coding conventions,
such as [PEP 8](https://peps.python.org/pep-0008/) and [PEP 257](https://peps.python.org/pep-0257/).
This coding conventions are enforced via `ruff`.

## Naming conventions

Do not use digits as abbreviations for words (e.g. `2` for "to", `4` for "for").

```python
# Good
def convert_ast_to_cst(node): ...


# Bad
def convert_ast2cst(node): ...
```

## Disabling checks

Disable a lint or type check locally, on the specific line that triggers it — not for a whole file or project.
Add a comment explaining why the check is disabled.

If the check is disabled to work around a bug in the current tooling rather than a deliberate exception,
add `RECHECK when <tool> is updated` to the comment, so the suppression can be removed once the tooling is fixed.

```python
value = some_call()  # noqa: E501 RECHECK when ruff is updated (false positive on this line, see ruff#1234)
```

## Lint and type-check budgets

`pyproject.toml` configures the `ruff` rules and the `pyright` mode that the whole repository already passes,
so CI fails on any new violation of those.
The stricter settings we still want — all `ruff` rules and `pyright`'s `strict` mode — are not enabled there yet,
because the existing issues would fail every build.
Instead of disabling those checks, their issues are *budgeted* by `tools/lint_budget.py`:

* the strict settings live in the script (`ruff --select ALL`) and in `pyrightconfig.strict.json`;
* `lint-budget.json` records how many issues of each kind (`ruff` rule code, `pyright` rule name) currently exist;
* CI runs `python tools/lint_budget.py --check` and fails when a pull request exceeds the budget of any kind,
  so no new issue of any kind can be introduced;
* run `python tools/lint_budget.py` locally after fixing issues: it lowers the budget to the new counts,
  and the lowered `lint-budget.json` is committed with the fix, so the counts can only ratchet down;
* `--init` records the current counts as the budget; use it only for the first run or an approved exception.

Once every count has reached zero, the script says so: move the strict settings into `pyproject.toml`
and delete `lint-budget.json`, `pyrightconfig.strict.json`, `tools/lint_budget.py` and the CI step.

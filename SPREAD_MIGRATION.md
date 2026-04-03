# Spread Testing Migration Plan — pyroscope-operators

This document breaks down the work needed to convert the pyroscope-operators
charm testing infrastructure to use **spread** via `charmcraft test`, as
described in `SPEC.md`. Each task is scoped so that it can be executed by an
LLM agent with minimal ambiguity.

> **Scope**: This plan focuses on the *spread testing conversion*. Feature-file
> reorganisation (the other half of the SPEC) is tracked separately.

---

## Status

| Task | Description | State |
|------|-------------|-------|
| 0 | Validate `charmcraft test` invocation (spike) | ✅ Done |
| 1 | Create project-level `spread.yaml` | ✅ Done |
| 2 | Create `spread/.extension` helper script | ✅ Done |
| 3 | Create unit-tests spread suite | ✅ Done |
| 4 | Create integration-tests spread suite (scaffold) | ✅ Done |
| 5 | Create `task.yaml` for each integration test file | ✅ Done |
| 6 | Create `task.yaml` for interface tests | ⬜ Pending |
| 7 | Update GitHub Actions CI to use `charmcraft test` | ⬜ Pending |
| 8 | Verify full spread run (end-to-end) | ✅ Done |
| 9 | Documentation updates | ⬜ Pending |

## Verification policy

> Each task must be verified with `charmcraft test <suite>` **before** being
> marked Done.  Do not defer verification to Task 8.  Catching failures
> close to the task that introduced them is far cheaper than debugging a
> pile of broken tasks at the end.

Practical notes:
- Run `charmcraft test` from `coordinator/` (where `spread.yaml` lives).
- LXD VMs are available locally; the `lxd-vm` backend in `spread/.extension`
  handles allocation.
- `backend-prepare` (in `spread/.extension`) runs `apt-get update` and basic
  system hardening. Tool installation (`tox`, `uv`, `microk8s`, `juju`) is done
  in per-suite `prepare:` blocks in `spread.yaml`, not in `.extension`.
- The integration suite prepare also enables MetalLB (required for Traefik),
  waits for each MicroK8s addon rollout before proceeding, and disables swap.

---

## Performance comparison

These numbers reflect wall-clock time measured on the local development machine
(LXD VM backend).  The spread column includes every phase: VM allocation, OS
boot, `backend-prepare`, `prepare-each`, the actual test run, `restore-each`,
`restore`, and VM discard.  Update this table whenever a new suite is verified.

### Unit tests

| Phase | Duration |
|-------|----------|
| VM allocation + boot | ~44 s |
| `backend-prepare` (apt update, install tox + uv) | ~73 s |
| `prepare-each` | <1 s |
| Test execution (`tox -e unit`, coordinator + worker) | ~30 s |
| `restore` + VM discard | ~1 s |
| **Total (`charmcraft test spread/unit/`)** | **~3 m 02 s** |
| **Direct `tox -e unit` (host, warm env)** | **~24 s** |

Spread adds roughly **2 m 38 s** of infrastructure overhead per run.  Most of
that cost is paid once per suite invocation (VM boot + OS setup), not per
task — so suites with many tasks will see a proportionally smaller overhead
ratio.  In CI the VM is already provisioned by the runner, so the `backend-prepare`
cost becomes the dominant overhead (~1 m) rather than VM boot.

### Integration tests

The full suite (`charmcraft test spread/integration/`) was verified passing with all
8 tasks — 6 skipped (pytest.mark.skip), 2 active (ingress, scaling-monolithic).
Timings measured on the local development machine (LXD VM backend):

| Phase | Duration |
|-------|----------|
| VM allocation + boot | ~33 s |
| `backend-prepare` (system hardening) | ~16 s |
| `prepare` (snap installs, MicroK8s enable + rollout, MetalLB, Juju bootstrap) | ~5 m |
| Tasks 1–6 (5 skipped + scaling-monolithic) | ~13 m |
| Task 7 (ingress, 10 tests) | ~6 m |
| Task 8 (profiling, skipped) | ~3 s |
| `restore` (destroy controller) + VM discard | ~15 s |
| **Total (`charmcraft test spread/integration/`)** | **~25 m** |
| **Direct `tox -e integration` (host, warm env)** | **TBD** |

The MicroK8s + Juju bootstrap phase (~5 min) is paid **once per suite
invocation**, not per task — the same VM is reused across all tasks in a run.
Skipped tasks complete in ~2 s each (pytest collects and reports skip immediately).
Active tests (ingress: ~6 m, scaling-monolithic: ~12 m) dominate the runtime.

---

## Context

| Aspect | Current state |
|--------|--------------|
| **Unit tests** | `tox -e unit` → pytest, delegated per-charm (`coordinator/tests/unit/`, `worker/tests/unit/`). 13 coordinator + 4 worker test files. All passing (99 % coverage). |
| **Interface tests** | Run inside `tox -e unit` for coordinator, separate `tox -e interface` for worker. Uses `InterfaceTester`. |
| **Integration tests** | `tox -e integration` → pytest in `coordinator/tests/integration/` (moved from repo root `tests/integration/` to live inside the coordinator directory tree, which is the unit charmcraft syncs to the spread VM; repo-root symlink maintained for `tox` compatibility). 8 test files; 2 active (`test_ingress.py`, `test_scaling_monolithic.py`), 6 skipped (profiling / retention / self-monitoring, Issues #291 and #315). 6 BDD feature files already exist. |
| **CI** | GitHub Actions using `canonical/observability` reusable workflows (`charm-pull-request.yaml`, `charm-quality-gates.yaml`). No spread today. |
| **Spread** | `coordinator/spread.yaml` present. `coordinator/spread/.extension` present. Smoke suite (`spread/hello/`) verified passing. Unit suite (`spread/unit/`) verified passing. Integration suite fully verified: `charmcraft test spread/integration/` passes all 8 tasks (6 skipped, 2 active). |
| **charmcraft** | v4.0.1 installed; `charmcraft test` available (wraps spread with a managed craft backend). |

### Key reference
- `canonical/charmcraft` repo contains a production `spread.yaml` + `spread/.extension` helper and suites under `tests/spread/` and `docs/howto/code/` that serve as the canonical pattern.
- Spread docs: <https://github.com/canonical/spread>

---

## Task Breakdown

### Task 0 — Validate `charmcraft test` invocation (spike)

> **Status: ✅ Done.** Findings documented below and in `coordinator/spread.yaml`.

**Goal**: Confirm the minimum viable `spread.yaml` that `charmcraft test` accepts for this charm and understand the craft-managed backend behaviour.

**Steps**:
1. In either `coordinator/` or at the repo root, create a minimal `spread.yaml` with:
   - A single `craft` backend (the one `charmcraft test` injects automatically) *or* a `ci` adhoc backend matching the pattern in `canonical/charmcraft`.
   - One trivial suite (`spread/hello/`) with a `task.yaml` that runs `echo hello`.
2. Run `charmcraft test` from the charm directory and observe:
   - Does it require a `spread.yaml` at the project root, or inside each charm dir?
   - Does it synthesise its own backend or expect one in `spread.yaml`?
   - What is the working directory inside the spread environment?
3. Document findings in a short comment at the top of `spread.yaml`.
4. Clean up the hello-world task (or keep it as a `manual: true` smoke test).

**Acceptance**: `charmcraft test` succeeds on at least one trivial task and the behaviour is understood.

**Findings** (also recorded in `coordinator/spread.yaml`):

1. **Location**: `spread.yaml` must live in the charm directory (same dir as
   `charmcraft.yaml`). `charmcraft test` is invoked from the charm directory
   and reads `spread.yaml` from there. A repo-root `spread.yaml` is not used.

2. **Craft backend**: charmcraft auto-injects the `craft:` backend at runtime.
   The system name must match the host distro string produced by
   `craft_platforms.DistroBase` (e.g. `ubuntu-24.04`). Only `systems:` is
   needed in `spread.yaml` — all other backend fields are injected.

3. **Path / env**: charmcraft processes `spread.yaml` into a temporary file
   that hard-codes `path: /root/proj`, `PROJECT_PATH: /root/proj`, and
   `CRAFT_ARTIFACT: $PROJECT_PATH/<charm-filename>`.
   Do **not** declare `path:`, `PROJECT_PATH:`, or a top-level `environment:`
   block — charmcraft injects them unconditionally and the validator rejects
   the extra keys (`Extra inputs are not permitted`).

4. **Reroot**: charmcraft adds `reroot: ".."` so spread resolves all suite/task
   paths relative to the charm directory. Suite keys such as `spread/hello/`
   map to `coordinator/spread/hello/`.

5. **Extension script**: `craft_application` generates allocate/discard/prepare/
   restore hooks that call `spread/.extension` with the backend name
   (`lxd-vm` locally, `ci` in CI). The script lives at
   `coordinator/spread/.extension`.

6. **Task structure**: each suite directory contains task *subdirectories*, each
   holding a `task.yaml`. A `task.yaml` placed directly at the suite root is
   **not** discovered by spread.
   - Correct: `spread/<suite>/<task>/task.yaml`
   - Wrong: `spread/<suite>/task.yaml` ← silently ignored

7. **Suite systems required**: every suite must list at least one system.
   An omitted `systems:` serialises as `systems: []` which causes
   "nothing matches provider filter" at runtime.

8. **Backend isolation**: using bare system names (e.g. `ubuntu-24.04`) causes
   spread to run the suite on **all** backends that publish that system. Adding
   a `ci` adhoc backend to `spread.yaml` therefore makes the CI allocator run
   during local `charmcraft test` runs, causing failures. The `ci` backend is
   intentionally omitted from `spread.yaml`; it is added by the GitHub Actions
   workflow (Task 7). Backend-qualified system names
   (`craft:ubuntu-24.04`) are rejected by `CraftSpreadYaml` and cannot be used
   as a workaround.

---

### Task 1 — Create project-level `spread.yaml`

> **Status: ✅ Done.** File: `coordinator/spread.yaml`.

**Goal**: Add the spread project configuration that all suites will use.

**Deliverables** — `coordinator/spread.yaml` (per-charm, per Finding 1 above).

**Deviations from original plan template**:
- `path:` and `PROJECT_PATH:` omitted (injected by charmcraft — Finding 3).
- Top-level `environment:` omitted (rejected by `CraftSpreadYaml` — Finding 3).
  Per-suite `environment:` blocks are permitted and used for the integration suite.
- `ci` backend omitted (would trigger CI allocator locally — Finding 8).
  It will be added in the GitHub Actions workflow (Task 7).
- `lxd-vm` backend omitted for the same reason; can be added locally by developers
  who have LXD available.
- Suite `systems:` use bare names (`ubuntu-24.04`) since backend-qualified names
  are rejected by the validator (Finding 8).

**Actual content** (see `coordinator/spread.yaml` for the canonical copy):
```yaml
project: pyroscope-coordinator-k8s

exclude:
  - .git
  - .tox
  - .venv
  - ".*_cache"

backends:
  craft:
    systems:
      - ubuntu-24.04

suites:
  spread/hello/:
    summary: Trivial smoke test (Task 0 spike)
    manual: true
    systems:
      - ubuntu-24.04

  spread/unit/:
    summary: Unit tests (coordinator + worker)
    systems:
      - ubuntu-24.04

  spread/interface/:
    summary: Interface compliance tests
    systems:
      - ubuntu-24.04

  spread/integration/:
    summary: Integration tests
    kill-timeout: 120m
    systems:
      - ubuntu-24.04
    environment:
      COORDINATOR_CHARM_PATH: "$PROJECT_PATH/coordinator"
      WORKER_CHARM_PATH: "$PROJECT_PATH/worker"
      COORDINATOR_CHARM_CHANNEL: "latest/edge"
      WORKER_CHARM_CHANNEL: "latest/edge"
```

---

### Task 2 — Create `spread/.extension` helper script

> **Status: ✅ Done.** File: `coordinator/spread/.extension`.

**Goal**: Provide the allocate / discard / prepare / restore shell helper for the adhoc CI backend, following the `canonical/charmcraft` pattern.

**Deliverables**: `spread/.extension` (executable bash script).

**Agent instructions**:
- Model it on `canonical/charmcraft/spread/.extension`.
- For the `ci` backend, `allocate` prints `localhost`, `discard` is a no-op.
- `backend-prepare`: `apt-get update`, install `snapd`, `charmcraft`, `juju` snap, and `uv` snap. Hold snap refreshes.
- `backend-restore`: clean up `$PROJECT_PATH`.
- `backend-prepare-each` / `backend-restore-each`: no-op for now.
- Mark the file `chmod +x`.

---

### Task 3 — Create the **unit-tests** spread suite

> **Status: ✅ Done.** Files: `coordinator/spread/unit/all/task.yaml`, `coordinator/spread/.extension` (updated to install tox + uv).

**Goal**: Wrap the existing `tox -e unit` invocation in a spread task so that unit tests can be run via `charmcraft test spread/unit/`.

**Directory layout**:
```
spread/
  unit/
    all/
      task.yaml
```

**`spread/unit/all/task.yaml`**:
```yaml
summary: Run all unit tests (coordinator + worker)

execute: |
  cd "$PROJECT_PATH"
  tox -e unit
```

**Agent instructions**:
- The `prepare` / `restore` at suite level should ensure tox and uv are available (they should be from Task 2).
- No Juju or K8s dependencies.
- Optionally split into `spread/unit/coordinator/task.yaml` and `spread/unit/worker/task.yaml` if independent runs are desired. This would enable parallel execution.

**Acceptance**: `charmcraft test spread/unit/` runs and all unit tests pass.

---

### Task 4 — Create the **integration-tests** spread suite (scaffold)

> **Status: ✅ Done.** Full suite (`charmcraft test spread/integration/`) verified
> passing with all 8 tasks.

**Goal**: Set up the suite-level `prepare` and `restore` scripts that bootstrap a Juju + MicroK8s environment for integration tests.

**Findings / deviations from original plan**:

- Tool installation (`uv`, `microk8s`, `juju` snaps) was moved out of
  `spread/.extension` and into the integration suite `prepare:` in `spread.yaml`.
- MetalLB must be enabled (needed for Traefik `LoadBalancer` service in the
  ingress test). The charm-dev multipass blueprint was the reference.
- Each MicroK8s addon must be waited on individually (rollout status) before
  proceeding; racing the next addon or Juju bootstrap against an unready addon
  caused hangs in earlier runs.
- Swap must be explicitly disabled inside the VM (`swapoff -a`) to avoid
  memory-pressure propagating to the host (the root cause of the original OOM
  / heavy-swap failures at 16 GB RAM).
- `COORDINATOR_CHARM_PATH` is set to `$CRAFT_ARTIFACT` (the `.charm` file
  packed by charmcraft) rather than a source directory. `COORDINATOR_CHARM_CHANNEL`
  must **not** be set alongside it — `helpers.py` checks channel before path,
  so setting both silently deploys from charmhub.
- `tests/integration/` and `scripts/` had to be **physically moved** into
  `coordinator/` (from the repo root) because charmcraft only syncs the charm
  directory to the spread VM and does not follow symlinks when packing.
  Repo-root symlinks (`tests/integration → coordinator/tests/integration`,
  `scripts → coordinator/scripts`) preserve the existing `tox -e integration`
  workflow.
- `pythonpath = ["."]` was added to `[tool.pytest.ini_options]` in
  `coordinator/pyproject.toml` so that `from tests.integration.helpers import …`
  resolves when pytest runs from `$PROJECT_PATH` (= `coordinator/` root in the VM).
- `prime: [-tests, -scripts]` was added to `charmcraft.yaml` to exclude the
  test/script directories from the `.charm` bundle itself.
- `discard_lxdvm` in `spread/.extension` was fixed: MicroK8s installs the
  Calico CNI, which adds a second interface to every VM. This causes `lxc ls
  -f csv` to quote and wrap the IPv4 field, breaking the original
  `grep ",$IP "` pattern. The fix matches on `"$IP "` (without leading comma).
- `prepare-each` was removed and `restore-each` was changed to use `--no-wait`
  (see Task 5 findings for the full explanation).

**Directory layout**:
```
spread/
  integration/
    task.yaml          # suite-level (optional, could go in spread.yaml)
```

**Suite-level prepare** (in `spread.yaml` or as a suite `prepare` field):
```bash
# Install and configure MicroK8s + Juju
snap install microk8s --channel=1.32/stable --classic
snap install juju --channel=3.6/stable

microk8s status --wait-ready --timeout 360
microk8s enable hostpath-storage dns registry

# Bootstrap Juju controller
microk8s config | juju add-k8s my-k8s --client
juju bootstrap my-k8s test-controller --config bootstrap-timeout=500
```

**Suite-level `prepare-each`**:
```bash
juju add-model "test-${SPREAD_TASK}"
```

**Suite-level `restore-each`**:
```bash
juju destroy-model --force --no-prompt --destroy-storage "test-${SPREAD_TASK}" || true
```

**Suite-level `restore`**:
```bash
juju destroy-controller --force --destroy-all-models --destroy-storage --no-prompt --no-wait test-controller || true
```

**Agent instructions**:
- This is the most infrastructure-heavy task. Use the `charmcraft` repo's `docs/howto/code/` suite prepare as a reference.
- `kill-timeout` should be generous (120m) since Juju bootstrapping and charm deployments take time.
- Environment variables `COORDINATOR_CHARM_PATH`, `WORKER_CHARM_PATH`, `COORDINATOR_CHARM_CHANNEL`, `WORKER_CHARM_CHANNEL` should be forwarded from `spread.yaml` environment.
- Pack the charms in prepare (or pass pre-built charm paths via env vars).

**Acceptance**: `charmcraft test spread/integration/` bootstraps a Juju environment and tears it down cleanly.

---

### Task 5 — Create `task.yaml` for each integration test file

> **Status: ✅ Done.** All 8 `task.yaml` files verified passing end-to-end via
> `charmcraft test spread/integration/` (6 skipped, 2 active — ingress and
> scaling-monolithic both passed).

**Goal**: One spread task per existing integration test file, each calling pytest.

**Findings from full-suite run**:

- **Duplicate Juju model creation** (fixed): The original design used
  `prepare-each` to create a model (`juju add-model test-<task>`) before each
  task. `pytest_jubilant` (invoked for active tests) independently creates its
  own model with the same prefix + random suffix. This doubled the number of
  concurrent model create/destroy cycles, overloading the Juju controller in the
  LXD VM and causing `restore-each` to hang for 15+ minutes per task on an
  otherwise-empty model.
  - **Fix**: Removed `prepare-each` from `spread/integration/` in `spread.yaml`.
    `pytest_jubilant` creates and destroys models on its own for active tests.
    For skipped tests, no model is ever created, and `restore-each`'s `|| true`
    handles the "model not found" error instantly.
  - **Fix**: Changed `restore-each` to pass `--no-wait` to `juju destroy-model`
    so that any model left behind by a failed active test is deleted
    asynchronously, without blocking the next task. The suite-level `restore:`
    destroys the whole controller, ensuring full cleanup.
  - **Fix**: Added `--model="test-${SPREAD_TASK##*/}"` to each task's pytest
    invocation. When `pytest_jubilant` receives `--model`, it reuses the
    model name deterministically (no random suffix) rather than generating one,
    making debug/log correlation easier.

- **OCI image resources missing** (fixed): `helpers.py` returned `None` for
  resources when `COORDINATOR_CHARM_PATH` pointed to a `.charm` file, relying
  on the incorrect assumption that OCI images are "embedded". Juju requires
  resource URIs at deploy time for local charms. Fix: changed the `.charm`
  branch in `charm_and_channel_and_resources` to call
  `get_resources(charm_path.parent)`, which reads the `upstream-source` OCI
  image URIs from `charmcraft.yaml` in the same directory as the packed charm.

- **Wrong worker charm channel** (fixed): `spread.yaml` set
  `WORKER_CHARM_CHANNEL: "latest/edge"` which does not exist for
  `pyroscope-worker-k8s` (only `2/stable`, `2/edge`, etc. exist). Fixed to
  `WORKER_CHARM_CHANNEL: "2/edge"`.

**Directory layout**:
```
spread/integration/
  ingress/task.yaml
  profiling/task.yaml
  profiling-tls/task.yaml
  profiling-with-collector/task.yaml
  profiling-with-collector-tls/task.yaml
  retention/task.yaml
  scaling-monolithic/task.yaml
  self-monitoring/task.yaml
```

**Example — `spread/integration/profiling/task.yaml`**:
```yaml
summary: Test OTLP gRPC profile ingestion

execute: |
  cd "$PROJECT_PATH"
  uv run --frozen --isolated --all-extras \
    pytest --exitfirst --model="test-${SPREAD_TASK##*/}" tests/integration/test_profiling.py -v
```

**Example — `spread/integration/self-monitoring/task.yaml`**:
```yaml
summary: Test COS integrations (metrics, logging, tracing, dashboards)
kill-timeout: 90m

execute: |
  cd "$PROJECT_PATH"
  uv run --frozen --isolated --all-extras \
    pytest --exitfirst --model="test-${SPREAD_TASK##*/}" tests/integration/test_self_monitoring.py -v
```

**Agent instructions**:
- Each `task.yaml` should set an appropriate `kill-timeout` (default 15 min is too short for integration tests — use 60m–90m).
- Tests that are currently skipped should still have `task.yaml` files created. The skip markers in the Python code will cause them to be reported as skipped, which is correct.
- Do NOT modify the existing Python test files in this task. The spread layer is an *addition*, not a replacement.
- Use `priority` to schedule long tests (self-monitoring, profiling-with-collector-tls) first for better parallelism.
- Optionally mark heavy tasks with `manual: true` if they should not run by default.

**Acceptance**: Each `task.yaml` is syntactically correct and references the right test file.

---

### Task 6 — Create `task.yaml` for interface tests

**Goal**: Wrap interface tests in spread tasks.

**Directory layout**:
```
spread/
  interface/
    coordinator/task.yaml
    worker/task.yaml
```

**Example — `spread/interface/coordinator/task.yaml`**:
```yaml
summary: Run coordinator interface compliance tests

execute: |
  cd "$PROJECT_PATH/coordinator"
  tox -e unit  # interface tests are bundled into the unit env
```

*(Or, if split out)*:
```yaml
execute: |
  cd "$PROJECT_PATH/coordinator"
  uv run --frozen --isolated pytest tests/interface -v
```

**Agent instructions**:
- Interface tests are lightweight (no Juju needed) — keep prepare/restore minimal.
- Review `coordinator/tox.ini` and `worker/tox.ini` to determine the exact invocation.

---

### Task 7 — Update GitHub Actions CI to use `charmcraft test`

**Goal**: Add (or replace) CI workflow steps that invoke `charmcraft test`.

**Agent instructions**:
1. Update the workflow file `.github/workflows/pull-request.yaml` (or update `pull-request.yaml`).
2. The workflow should:
   - Check out the repo.
   - Install `charmcraft` snap.
   - Run `charmcraft test` (or `spread` directly with the `ci` backend).
3. The existing `canonical/observability` reusable workflows should remain **as-is** for now (they handle lint, unit, and the current integration path). The spread workflow is an *addition* during the migration period.
4. Consider a matrix strategy: one job per integration task for maximum parallelism.
5. Add a `workflow_dispatch` trigger for manual runs during development.

**Reference**: look at how `canonical/charmcraft` `.github/workflows/` invokes spread.

**Acceptance**: The workflow runs on a PR branch without errors (at least for integration tests).

---

### Task 8 — Verify full spread run (end-to-end)

> **Status: ✅ Done.** All 8 integration tasks verified passing via
> `charmcraft test spread/integration/`. Full suite runtime: ~25 minutes.

**Goal**: Run `charmcraft test` (or the CI workflow) end-to-end and fix any issues.

**Results** (`charmcraft test spread/integration/`, fourth run):

| Task | Tests | Result | Duration |
|---|---|---|---|
| profiling-with-collector | 0 run (all skipped) | PASS | ~2 s |
| profiling-with-collector-tls | 0 run (all skipped) | PASS | ~2 s |
| self-monitoring | 0 run (all skipped) | PASS | ~2 s |
| profiling-tls | 0 run (all skipped) | PASS | ~2 s |
| retention | 0 run (all skipped) | PASS | ~2 s |
| profiling | 0 run (all skipped) | PASS | ~3 s |
| scaling-monolithic | 4 tests PASSED | PASS | ~12 min |
| ingress | 10 tests PASSED | PASS | ~6 min |

Three bugs were found and fixed during the full-suite run:
1. **Duplicate model lifecycle** — see Task 5 findings.
2. **OCI image resources missing** — see Task 5 findings.
3. **Wrong worker charm channel** — see Task 5 findings.

**Acceptance**: All currently-passing tests also pass under spread.

---

### Task 9 — Documentation updates

**Goal**: Update repo docs to reflect the new spread testing setup.

**Agent instructions**:
1. Update `CONTRIBUTING.md`:
   - Add a section on running tests via `charmcraft test`.
   - Document how to run specific suites / tasks.
   - Document the `spread.yaml` structure.
2. Update `README.md` if it references test commands.
3. Keep the existing `tox -e unit` / `tox -e integration` commands working (they are not removed).

---

## Dependency Graph

```
Task 0  (spike: validate charmcraft test)
  │
  ▼
Task 1  (spread.yaml)  ──►  Task 2  (spread/.extension)
  │                              │
  ├──────────────────────────────┤
  │                              │
  ▼                              ▼
Task 3  (unit suite)       Task 4  (integration suite scaffold)
  │                              │
  │                              ▼
  │                        Task 5  (integration task.yaml files)
  │                              │
  ▼                              │
Task 6  (interface suite)        │
  │                              │
  ├──────────────────────────────┤
  ▼                              ▼
Task 7  (CI workflow)
  │
  ▼
Task 8  (E2E verification)
  │
  ▼
Task 9  (Documentation)
```

Tasks 3, 4, and 6 can be worked on in **parallel** once Tasks 1 and 2 are done.
Tasks 5 depends on Task 4. Tasks 7–9 are sequential.

---

## Files to create (summary)

| File | Task |
|------|------|
| `spread.yaml` | 1 |
| `spread/.extension` | 2 |
| `spread/unit/all/task.yaml` (or per-charm split) | 3 |
| `spread/integration/ingress/task.yaml` | 5 |
| `spread/integration/profiling/task.yaml` | 5 |
| `spread/integration/profiling-tls/task.yaml` | 5 |
| `spread/integration/profiling-with-collector/task.yaml` | 5 |
| `spread/integration/profiling-with-collector-tls/task.yaml` | 5 |
| `spread/integration/retention/task.yaml` | 5 |
| `spread/integration/scaling-monolithic/task.yaml` | 5 |
| `spread/integration/self-monitoring/task.yaml` | 5 |
| `spread/interface/coordinator/task.yaml` | 6 |
| `spread/interface/worker/task.yaml` | 6 |
| `.github/workflows/spread-tests.yaml` | 7 |

## Files to modify (summary)

| File | Task |
|------|------|
| `CONTRIBUTING.md` | 9 |
| `README.md` (if needed) | 9 |

> **Note**: `tests/integration/helpers.py` and `coordinator/pyproject.toml`
> were modified as part of Tasks 4/5 to support the spread environment
> (pre-built `.charm` path handling and `pythonpath`). The spread layer still
> wraps the existing pytest invocations without altering test logic.

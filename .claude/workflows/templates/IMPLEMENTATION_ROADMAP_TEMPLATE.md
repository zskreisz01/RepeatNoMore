# Implementation Roadmap: ${ROADMAP_ID}

**Created**: ${TIMESTAMP}
**Branch**: ${BRANCH_NAME}
**Status**: IN_PROGRESS | COMPLETED | BLOCKED

## Task Overview

### Original Request
${WORKFLOW_TASK}

### Goals
1. Primary goal description
2. Secondary goals
3. Non-goals (what this does NOT include)

## Current State Analysis

### Components Affected
- [ ] Component 1 - Description of current state
- [ ] Component 2 - Description of current state
- [ ] Component 3 - Description of current state

### Dependencies to Review
- Dependency 1: Current usage, potential elimination
- Dependency 2: Current usage, required changes

### Files to Modify
```
app/
├── file1.py         # Change description
├── file2.py         # Change description
└── config.py        # Change description

tests/
├── test_file1.py    # Test updates needed
└── test_file2.py    # New tests needed

azure/
├── scripts/         # Deployment changes
└── infra/           # Infrastructure changes
```

## Implementation Plan

### Phase 1: Foundation Changes
**Status**: PENDING | IN_PROGRESS | COMPLETED

**Objective**: Description of phase objective

**Tasks**:
- [ ] Task 1.1: Description
- [ ] Task 1.2: Description
- [ ] Task 1.3: Description

**Files Changed**:
- `path/to/file.py`: Description of change

**Validation**:
- Unit tests: `pytest tests/unit/test_xxx.py`
- Manual check: Description

---

### Phase 2: Core Implementation
**Status**: PENDING | IN_PROGRESS | COMPLETED

**Objective**: Description of phase objective

**Tasks**:
- [ ] Task 2.1: Description
- [ ] Task 2.2: Description
- [ ] Task 2.3: Description

**Files Changed**:
- `path/to/file.py`: Description of change

**Validation**:
- Unit tests: `pytest tests/unit/test_xxx.py`
- Integration: Description

---

### Phase 3: Integration and Migration
**Status**: PENDING | IN_PROGRESS | COMPLETED

**Objective**: Description of phase objective

**Tasks**:
- [ ] Task 3.1: Description
- [ ] Task 3.2: Description
- [ ] Task 3.3: Description

**Files Changed**:
- `path/to/file.py`: Description of change

**Validation**:
- Full test suite: `make test`
- Docker validation: `docker-compose up -d && docker-compose logs`

---

### Phase 4: Cleanup and Documentation
**Status**: PENDING | IN_PROGRESS | COMPLETED

**Objective**: Remove old code, update documentation

**Tasks**:
- [ ] Remove deprecated code
- [ ] Update `_docs/DESIGN_DECISIONS.md`
- [ ] Update `knowledge_base/docs/architecture.md`
- [ ] Update `CLAUDE.md` if needed
- [ ] Update Azure infrastructure docs

**Files Changed**:
- Documentation files

**Validation**:
- Documentation review
- Links and references check

## Success Criteria

### Must Have
- [ ] Criterion 1: Description
- [ ] Criterion 2: Description
- [ ] Criterion 3: All unit tests pass

### Should Have
- [ ] Criterion 4: Description
- [ ] Criterion 5: Docker logs show healthy startup

### Nice to Have
- [ ] Criterion 6: Description

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Risk 1 | High/Medium/Low | High/Medium/Low | Mitigation strategy |
| Risk 2 | High/Medium/Low | High/Medium/Low | Mitigation strategy |

## Rollback Plan

If the implementation fails or causes issues:

1. **Immediate Rollback**:
   ```bash
   git checkout main
   docker-compose down
   docker-compose up -d
   ```

2. **Data Recovery** (if applicable):
   - Step 1
   - Step 2

3. **Communication**:
   - Notify affected parties
   - Document failure for post-mortem

## Progress Log

### ${TIMESTAMP} - Phase 1 Started
- Notes...

### ${TIMESTAMP} - Phase 1 Completed
- Summary of changes...

## Final Notes

- Any additional context
- Lessons learned
- Follow-up tasks for future

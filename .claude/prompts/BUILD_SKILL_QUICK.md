# Quick Skill Builder Prompt

Copy this prompt and replace `{SUBSYSTEM}` with your target subsystem name.

---

## Prompt

```markdown
# Build Agent Skill: {SUBSYSTEM}

## Objective

Build a comprehensive Claude Code Agent Skill for the **{SUBSYSTEM}** subsystem in this repository.

## Workflow (MANDATORY)

Follow this exact sequence:

### Phase 1: EXPLORE (No coding yet)

Think hard and thoroughly explore the codebase:

1. **Search for all related files** using patterns:
   - "{subsystem}", "{subsystem_snake_case}", "{SubsystemPascalCase}"
   - Related domain terms and abbreviations

2. **For each file found, document:**
   - Full path
   - Purpose
   - Key exports (classes, functions, types)

3. **Map the architecture:**
   - Backend: routes, services, repositories, models, schemas, tasks
   - Frontend: pages, components, hooks, actions, types, i18n
   - Tests: unit, integration, e2e

4. **Extract patterns:**
   - Naming conventions
   - Error handling
   - Auth patterns
   - Validation patterns

### Phase 2: PLAN

Before writing any files:

1. **Define scope boundaries** (what IS and IS NOT covered)
2. **List 15-25 trigger phrases** that should activate this skill
3. **Outline each file's content**
4. **Identify MANDATORY patterns** that must be documented

### Phase 3: BUILD

Create the skill at `.claude/skills/{subsystem}/`:

```
{subsystem}/
├── SKILL.md          # <500 lines, essential info, links to others
├── REFERENCE.md      # Complete API, models, schemas
├── EXAMPLES.md       # Concrete code examples per layer
├── PATTERNS.md       # Critical implementation patterns
├── MODULES.md        # Complete file inventory
└── scripts/
    ├── README.md
    └── *.py          # Utility scripts (validate, check status, etc.)
```

**SKILL.md Requirements:**
- Valid YAML frontmatter (name, description, allowed-tools)
- Under 500 lines
- Quick reference tables
- Links to all supporting files
- Trigger phrases section
- Validation checklist

**Supporting Files:**
- REFERENCE.md: All APIs, models, types with full details
- EXAMPLES.md: Working code examples (4-6 per layer)
- PATTERNS.md: Critical patterns with DO and DON'T sections
- MODULES.md: Every file with path, purpose, exports

**Scripts:**
- 2-4 utility scripts
- Self-contained (no external deps when possible)
- CLI with argparse and help text
- Work offline when possible

### Phase 4: VERIFY

Confirm:
- [ ] All files documented in MODULES.md
- [ ] All APIs documented in REFERENCE.md
- [ ] Examples follow actual codebase patterns
- [ ] SKILL.md under 500 lines
- [ ] No invented paths or patterns
- [ ] Scripts are executable

## Constraints

- Base everything on DISCOVERED code (no invention)
- Reuse existing patterns (no new conventions)
- Use progressive disclosure (details in supporting files)
- Keep scripts dependency-free when possible

## Output

After completion, report:
- Files created with line counts
- Confirmation SKILL.md < 500 lines
- List of utility scripts
```

---

## Usage Examples

**Authentication:**
```
# Build Agent Skill: authentication

Focus on: login/logout, JWT tokens, LDAP, RBAC, sessions
```

**User Management:**
```
# Build Agent Skill: user-management

Focus on: user CRUD, roles, permissions, profile management
```

**Meal Requests:**
```
# Build Agent Skill: meal-requests

Focus on: request CRUD, approval workflow, meal types, reporting
```

**Reporting:**
```
# Build Agent Skill: reporting

Focus on: analytics endpoints, data aggregation, export formats
```

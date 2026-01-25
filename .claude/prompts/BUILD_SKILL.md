# Build Agent Skill Prompt

Use this prompt to instruct Claude Code to build a comprehensive Agent Skill for a specific subsystem in your codebase.

---

## INSTRUCTIONS

You are a senior developer building a **Claude Code Agent Skill** for a specific subsystem. Follow the official skills specification and best practices rigorously.

**Your workflow MUST be:**
1. **EXPLORE** - Thoroughly research the codebase (NO coding yet)
2. **PLAN** - Design the skill structure and document findings
3. **BUILD** - Create all skill files with progressive disclosure
4. **VERIFY** - Validate completeness and correctness

**Think hard** before each phase. Use extended reasoning for complex analysis.

---

## CONTEXT

### What is an Agent Skill?
A skill teaches Claude Code how to work correctly with a specific subsystem. It provides:
- Authoritative file locations and module inventory
- Implementation patterns and conventions
- API references and data models
- Executable utility scripts
- Trigger phrases for activation

### Skill Structure (Official Specification)
```
.claude/skills/{skill-name}/
├── SKILL.md              # Main file (<500 lines) - essential info only
├── REFERENCE.md          # Detailed API/model documentation
├── EXAMPLES.md           # Concrete code examples
├── PATTERNS.md           # Implementation patterns & conventions
├── MODULES.md            # Complete module inventory
└── scripts/              # Executable utilities (run via bash, not loaded)
    ├── README.md
    └── *.py / *.sh
```

### Progressive Disclosure Principle
- **SKILL.md** loads on activation (keep focused, <500 lines)
- Supporting files load **only when Claude reads them**
- Scripts **execute** without loading content into context
- This minimizes token usage while providing comprehensive resources

---

## TASK

Build a comprehensive Agent Skill for: **`{SUBSYSTEM_NAME}`**

Replace `{SUBSYSTEM_NAME}` with the target subsystem (e.g., "authentication", "meal-requests", "user-management", "reporting").

---

## PHASE 1: EXPLORE (No Coding)

**Goal:** Thoroughly understand the subsystem before planning.

### 1.1 Discover All Related Files

Search for files related to the subsystem using multiple strategies:

```
Patterns to search:
- Direct matches: "{subsystem}", "{subsystem_snake}", "{SubsystemPascal}"
- Related terms: domain-specific keywords, abbreviations
- File types: models, schemas, routes, services, repositories, tasks, tests
- Frontend: pages, components, hooks, actions, types, i18n
```

**Document every file found with:**
- Full path relative to repo root
- File type and purpose
- Key exports (classes, functions, types)

### 1.2 Analyze Architecture

For each layer, identify:

**Backend:**
- [ ] API routes/endpoints (paths, methods, auth requirements)
- [ ] Service layer (business logic methods)
- [ ] Repository layer (database operations)
- [ ] Database models (tables, relationships, fields)
- [ ] Schemas (request/response Pydantic models)
- [ ] Background tasks (Celery, scheduled jobs)
- [ ] Utilities and helpers

**Frontend:**
- [ ] Pages and routes
- [ ] Components (shared, feature-specific)
- [ ] Hooks and state management
- [ ] Server actions / API calls
- [ ] TypeScript types and interfaces
- [ ] Internationalization keys

**Tests:**
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests

### 1.3 Extract Patterns

Identify:
- Naming conventions used
- Error handling patterns
- Authentication/authorization patterns
- Validation patterns
- Logging patterns
- Database transaction patterns
- Any subsystem-specific conventions

### 1.4 Map Dependencies

Create a dependency graph:
- What does this subsystem depend on?
- What depends on this subsystem?
- External integrations (APIs, services)

---

## PHASE 2: PLAN

**Goal:** Design the skill structure based on exploration findings.

### 2.1 Define Scope Boundaries

Clearly state:
- What this skill DOES cover (specific features, operations)
- What this skill does NOT cover (adjacent systems, out-of-scope features)
- How to handle requests that span multiple systems

### 2.2 Identify Trigger Phrases

List 15-25 phrases that should activate this skill:
- Feature names and synonyms
- Operation verbs (create, update, delete, list, etc.)
- Domain-specific terminology
- Common user query patterns

### 2.3 Plan File Structure

For each file, outline:
- **SKILL.md**: Core sections, essential quick-reference info
- **REFERENCE.md**: API endpoints, model schemas, type definitions
- **EXAMPLES.md**: 4-6 concrete code examples per layer
- **PATTERNS.md**: Critical patterns that MUST be followed
- **MODULES.md**: Complete file inventory with responsibilities
- **scripts/**: 2-4 utility scripts (validation, status checks, etc.)

### 2.4 Identify Critical Patterns

Document patterns that are **MANDATORY** to follow:
- Patterns that prevent bugs if followed
- Patterns that cause bugs if violated
- Security-critical patterns
- Performance-critical patterns

---

## PHASE 3: BUILD

**Goal:** Create all skill files following the plan.

### 3.1 Create Directory Structure

```bash
mkdir -p .claude/skills/{skill-name}/scripts
```

### 3.2 Write SKILL.md (Main File)

**Requirements:**
- MUST be under 500 lines
- MUST include valid YAML frontmatter
- MUST link to all supporting files
- MUST include trigger phrases section

**Frontmatter Template:**
```yaml
---
name: {skill-name-kebab-case}
description: |
  {What it does}. Use when working with {trigger contexts}.
  {Key capabilities in 1-2 sentences}.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---
```

**Required Sections:**
1. Overview (what, why, key technologies)
2. When to Use This Skill (activation triggers)
3. Quick Reference (tables of locations, endpoints)
4. Core Concepts (brief, link to REFERENCE.md for details)
5. Allowed/Prohibited Operations
6. Trigger Phrases
7. Validation Checklist
8. Links to Supporting Files

### 3.3 Write REFERENCE.md

Include:
- Complete database model definitions with field descriptions
- All API endpoints with request/response schemas
- Service layer method signatures
- Repository method signatures
- TypeScript type definitions
- Enum values and constants

### 3.4 Write EXAMPLES.md

Provide concrete examples for:
- Adding a new API endpoint
- Adding a service method
- Adding a repository method
- Creating new schemas
- Adding frontend components
- Adding server actions
- Writing tests

**Each example must:**
- Show the exact file to modify
- Include complete, working code
- Follow existing patterns
- Include imports

### 3.5 Write PATTERNS.md

Document critical patterns:
- Async/await patterns
- Error handling patterns
- Authentication patterns
- Database transaction patterns
- Celery task patterns (if applicable)
- Schema patterns (CamelModel inheritance)
- Testing patterns

**For each pattern:**
- Explain WHY it matters
- Show the CORRECT implementation
- Show WHAT NOT TO DO (anti-patterns)
- Include a checklist for verification

### 3.6 Write MODULES.md

Create comprehensive inventory:
- Every file with full path
- Purpose/responsibility
- Key exports (functions, classes, types)
- Dependencies
- "Where to add new code" guide

### 3.7 Create Utility Scripts

Build 2-4 scripts that:
- Execute without loading into context
- Provide validation or status checking
- Work offline when possible (no backend required)
- Include clear usage documentation

**Script Requirements:**
- Shebang line (`#!/usr/bin/env python3`)
- Argparse for CLI arguments
- Clear help text
- Exit codes (0 success, 1 failure)
- No external dependencies when possible

---

## PHASE 4: VERIFY

**Goal:** Validate the skill is complete and correct.

### 4.1 Completeness Checklist

- [ ] All discovered files are documented in MODULES.md
- [ ] All API endpoints are documented in REFERENCE.md
- [ ] All database models are documented with field descriptions
- [ ] Examples cover all major operations
- [ ] Patterns cover all critical conventions
- [ ] Scripts are executable and documented
- [ ] SKILL.md is under 500 lines
- [ ] All links between files are valid

### 4.2 Accuracy Checklist

- [ ] File paths are correct and exist
- [ ] Code examples follow actual codebase patterns
- [ ] Schema field names match actual models
- [ ] API endpoint paths are accurate
- [ ] No invented abstractions or patterns

### 4.3 Usability Checklist

- [ ] Trigger phrases cover common query patterns
- [ ] Quick reference tables are scannable
- [ ] Examples are copy-paste ready
- [ ] Patterns explain WHY, not just WHAT
- [ ] Scripts have clear usage instructions

---

## OUTPUT FORMAT

Create files in this order:
1. `.claude/skills/{skill-name}/SKILL.md`
2. `.claude/skills/{skill-name}/REFERENCE.md`
3. `.claude/skills/{skill-name}/EXAMPLES.md`
4. `.claude/skills/{skill-name}/PATTERNS.md`
5. `.claude/skills/{skill-name}/MODULES.md`
6. `.claude/skills/{skill-name}/scripts/README.md`
7. `.claude/skills/{skill-name}/scripts/*.py`

After completion, provide a summary:
- Total files created
- Line counts for each .md file
- List of utility scripts with descriptions
- Confirmation that SKILL.md is under 500 lines

---

## ANTI-PATTERNS TO AVOID

**DO NOT:**
- Invent file paths that don't exist
- Create patterns not used in the codebase
- Add untested conventions
- Make SKILL.md a dump of everything (use progressive disclosure)
- Skip the exploration phase
- Create scripts with external dependencies
- Include time-sensitive information
- Over-engineer the skill structure

**DO:**
- Base everything on actual discovered code
- Keep SKILL.md focused and scannable
- Put details in supporting files
- Make scripts self-contained
- Use concrete examples from the codebase
- Document the "why" behind patterns

---

## EXAMPLE USAGE

To build a skill for the authentication subsystem:

```
Build a comprehensive Agent Skill for: authentication

Focus on:
- Login/logout flows
- JWT token management
- LDAP integration
- Role-based access control
- Session handling
```

To build a skill for the meal request subsystem:

```
Build a comprehensive Agent Skill for: meal-requests

Focus on:
- Meal request CRUD operations
- Approval workflows
- Meal types and scheduling
- Department-based filtering
- Reporting and analytics
```

---

## REMEMBER

1. **Explore thoroughly** before planning (read files, don't assume)
2. **Think hard** during planning (use extended reasoning)
3. **Follow existing patterns** (don't invent new ones)
4. **Keep SKILL.md under 500 lines** (use progressive disclosure)
5. **Verify everything** (paths, patterns, examples must be accurate)

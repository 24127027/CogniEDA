# CogniEDA Wiki Skeleton - Creation Summary

**Investigation Completed**: 2026-08-14T17:55:53.157Z

---

## Deliverables

A comprehensive wiki skeleton for CogniEDA has been created with four main documents:

### 1. INDEX.md
**Navigation hub for the entire wiki**
- Quick overview of CogniEDA
- Documentation structure and navigation
- Core concepts summary
- Quick start guide
- Architecture at a glance
- Key components overview
- Implementation status
- Development setup
- Topic-based navigation
- Navigation by role (user, developer, architect)

**Purpose**: Entry point for all wiki users

---

### 2. CogniEDA_WIKI_SKELETON.md
**Main comprehensive wiki (12 parts)**

**Part 1: Concepts & Foundation**
- What is CogniEDA (core problem and solution)
- Research state separation (8 FCOs)
- Authority & governance model
- The validity sequence
- Epistemic roles independent of persistence

**Part 2: System Architecture**
- Three cooperating planes (Control, Specialist, Authority)
- Component responsibilities
- Data flow diagrams
- Message processing sequence
- Execution dispatch sequence

**Part 3: Data Model & Persistence**
- First-class objects (FCOs) definitions
- Non-FCO persisted entities
- Persistence model (SQLModel, SQLite)
- Admission boundary and transactions

**Part 4: Configuration System**
- Workspace structure
- Configuration files (project.toml, agents.toml, skills.toml, mcp.toml)
- Environment variables
- Runtime reload mechanisms

**Part 5: Runtime & Execution**
- Bootstrap sequence (9 steps)
- Message processing loop
- Planning consultation workflow
- Skill management commands
- Provider configuration commands

**Part 6: Agent Specializations**
- Planner agent (role, responsibilities, boundaries, I/O)
- Data Explorer (role, capabilities, methods)
- Hypothesis Analyst (target responsibilities, status)
- Graph Miner (target responsibilities, status)

**Part 7: Extension Points**
- Custom agent instructions
- Skills integration (pydantic_ai_skills)
- MCP server integration
- Model provider support
- Custom specialist providers
- Database customization

**Part 8: Execution Model**
- Capability-based dispatch
- Execution contracts (Request, Result)
- Task kinds and routing

**Part 9: Current Implementation Status**
- Fully implemented features (✅)
- Partially implemented (🔶)
- Deferred work (❌)
- MVP-v2 definition of done

**Part 10: API Reference**
- Key classes (Application, Workspace, Planner, Dispatcher, Registry, Agents)
- Key schemas (Objective, Task, Plan, PlannerResult, ExecutionRequest/Result, Message, ModelConfig)

**Part 11: Development**
- Setup instructions
- Configuration guidance
- Testing commands
- Debugging tips

**Part 12: Roadmap & Status**
- Current implementation boundary
- MVP-v2 target
- Blocked work and dependencies

---

### 3. CogniEDA_ARCHITECTURE_DEEP_DIVE.md
**In-depth technical design documentation**

**Section 1: Architecture Principles**
- Priority order (validity first)
- Core design pattern (authority separation)
- Why each principle matters

**Section 2: Three-Plane Architecture**
- Control Plane (Human, Planner, Workspace)
- Specialist Plane (Providers, Registry, Dispatcher)
- Authority Plane (Governance, Persistence, Validation)
- Visual architecture diagrams

**Section 3: Data Flow Architecture**
- User interaction boundary
- Message processing sequence
- Execution dispatch sequence
- State transitions

**Section 4: State Transitions and Validity**
- Authority sequence (proposal → discovery)
- Validity preservation (immutability, append-only, lineage, eligibility)
- Conditional paths and typed results

**Section 5: Component Interaction Patterns**
- Workspace-first initialization
- Provider resolution
- Agent factory pipeline
- Execution registry pattern

**Section 6: Boundary Contracts**
- ExecutionRequest contract
- ExecutionResult contract
- PlannerWorkOutcome contract

**Section 7: Configuration Evolution**
- Startup configuration (5 layers)
- Runtime configuration changes
- Provider switching workflow

**Section 8: Error Handling and Recovery**
- Execution failure handling
- Model credential errors
- Controlled planner errors

**Section 9: Extensibility Patterns**
- Adding custom capabilities
- Custom instructions
- Skills integration
- MCP servers
- Testing architecture
- Performance considerations
- Security considerations

---

### 4. CogniEDA_REFERENCE_GUIDE.md
**Complete API and workflow reference**

**Part 1: CLI and Entrypoints**
- cognieda command syntax
- Entrypoint flow

**Part 2: REPL Commands**
- Skill management (/skill add|rm|list|use|drop)
- Provider management (/provider list|use|model|key)
- System commands (/reload|exit|quit)

**Part 3: Core Classes and Methods**
- Application methods
- Workspace methods
- Planner methods
- ExecutorDispatcher methods
- ExecutorRegistry methods
- DataExplorer methods

**Part 4: Schema Reference**
- All enum types
- Core model classes with fields
- Contracts and data structures

**Part 5: Workflow Patterns**
- Initialize and launch pattern
- Add custom skill workflow
- Switch model provider workflow
- Create custom instructions workflow
- Programmatic execution pattern

**Part 6: Configuration Files Reference**
- project.toml structure and examples
- agents.toml structure and examples
- skills.toml structure and examples
- mcp.toml structure and examples
- .env format

**Part 7: Error Handling**
- Common errors and resolutions
- MissingModelCredentialError
- CapabilityNotRegisteredError
- PlannerErrorCode variants

**Part 8: Database Operations**
- SQLModel session usage
- Repository pattern
- Transaction boundaries

**Part 9: Testing Utilities**
- Fixtures (conftest.py)
- Example test patterns

**Part 10: Development Commands**
- Setup commands
- Run commands
- Testing commands
- Linting and type checking
- Verification commands

**Part 11: Troubleshooting**
- Common issues and solutions
- Debug techniques
- Performance issues
- Database issues

**Part 12: Performance Tuning**
- Conversation history management
- Provider instance caching
- Database optimization

**Part 13: Integration Examples**
- Integration with external systems
- Custom specialist provider implementation
- Advanced use cases

---

### 5. CogniEDA_INVESTIGATION_REPORT.md
**Raw investigation findings**

- Main purpose and design philosophy
- System architecture and boundaries
- Major components and responsibilities
- Data flow and message processing
- Agent architecture and specializations
- Persistence model
- Configuration system
- Key workflows
- Extension points
- Current implementation status (detailed)
- Key design decisions
- Recommended wiki structure

---

## Investigation Scope

**Files Analyzed**: 50+ source files including:

### Entry Points & CLI
- src/cognieda/cli/app.py
- src/cognieda/cli/main.py
- src/cognieda/__main__.py

### Runtime & Bootstrap
- src/cognieda/runtime/bootstrap.py
- src/cognieda/runtime/application.py
- src/cognieda/runtime/workspace.py
- src/cognieda/runtime/conversation.py

### Agents
- src/cognieda/agents/planner/agent.py
- src/cognieda/agents/data_explorer/agent.py
- src/cognieda/agents/hypothesis_analyst/agent.py
- src/cognieda/agents/graph_miner/agent.py

### Execution Layer
- src/cognieda/execution/dispatcher.py
- src/cognieda/execution/registry.py
- src/cognieda/execution/contracts.py
- src/cognieda/execution/capabilities.py

### Application Services
- src/cognieda/application/services/planner_commit.py
- src/cognieda/application/services/mvp_data_admission.py
- src/cognieda/application/ports/execution.py
- src/cognieda/application/ports/llm.py

### Infrastructure
- src/cognieda/infrastructure/llm/factory.py
- src/cognieda/infrastructure/agent_tooling/manager.py
- src/cognieda/infrastructure/persistence/models.py
- src/cognieda/infrastructure/persistence/session.py

### Schemas
- src/cognieda/schemas/artifacts.py
- src/cognieda/schemas/plan.py
- src/cognieda/schemas/enums.py
- src/cognieda/schemas/common.py
- src/cognieda/schemas/planner_operations.py
- src/cognieda/agents/planner/types.py

### Configuration & Docs
- config/agents.toml
- config/skills.toml
- config/mcp.toml
- docs/architecture/ (7 files)
- docs/what-is-cognieda.md
- AGENTS.md
- README.md
- pyproject.toml

### Tests
- tests/agents/planner/test_agent.py
- tests/cli/test_app.py
- tests/conftest.py

---

## Key Findings

### Architecture
- **Three-Plane Design**: Control (Human+Planner), Specialist (Providers), Authority (Governance+Persistence)
- **Eight FCOs**: Objective, DataProfile, Assumption, Task, Hypothesis, Evidence, Discovery, SessionFrame
- **Eight Authority Types**: Human, Planning, Execution, Scientific, Governance, Admission, Persistence, Validity-Transition
- **Validity Sequence**: Proposal → Approval → Execution → Observation → Evidence Admission → Evaluation → Governance → Discovery Admission

### Implementation Status
- **Fully Implemented**: Core schemas, immutable Plans, ConversationHistory, Workspace management, provider configuration, ExecutorRegistry/Dispatcher, Data Explorer, SQLite persistence, Planner REPL
- **Partially Implemented**: Hypothesis Analyst (scaffold), Graph Miner (stub), PlannerOperation commit
- **Deferred**: Human approval workflow, Plan activation, Task DAG runtime, Scientific protocol, Protected evaluation, Governance, Discovery admission, Semantic graph query, Restart safety, Multi-session resume

### Design Principles
1. **Validity and traceability** first (epistemic correctness)
2. **Type safety** for context boundaries
3. **Multi-session continuity** support
4. **Speed and convenience** after the above three

### Extension Points
- Custom instructions (AGENTS.md)
- Skills (pydantic_ai_skills + skills.toml)
- MCP servers (mcp.toml)
- Model providers (factory.py)
- Specialist providers (ExecutorProvider protocol)
- Database (COGNIEDA_DB_URL)
- Commands (Application._handle_command)

---

## Wiki Quality Metrics

| Metric | Value |
|--------|-------|
| **Total Documents** | 5 |
| **Total Sections** | 50+ |
| **Code Examples** | 30+ |
| **Diagrams** | 10+ (text-based) |
| **API Classes Documented** | 6 |
| **Schemas Documented** | 15+ |
| **Commands Documented** | 15+ |
| **Workflows Documented** | 8+ |
| **Configuration Files** | 4 |
| **Troubleshooting Tips** | 10+ |
| **Integration Examples** | 5+ |

---

## Navigation Paths

### For First-Time Users
1. INDEX.md (quick overview)
2. WIKI_SKELETON.md Part 1-2 (concepts and architecture)
3. REFERENCE_GUIDE.md Part 1-2 (CLI and commands)
4. Run `cognieda --mode mock`

### For Developers
1. WIKI_SKELETON.md Part 11 (development setup)
2. REFERENCE_GUIDE.md Part 3-4 (API and schemas)
3. ARCHITECTURE_DEEP_DIVE.md (system design)
4. REFERENCE_GUIDE.md Part 5 (workflows)
5. REFERENCE_GUIDE.md Part 13 (integration examples)

### For Architects
1. ARCHITECTURE_DEEP_DIVE.md (full design)
2. WIKI_SKELETON.md Part 2 (component responsibilities)
3. WIKI_SKELETON.md Part 8 (execution model)
4. REFERENCE_GUIDE.md Part 6 (contracts)

### For Contributors
1. WIKI_SKELETON.md Part 10-11 (extension points, development)
2. ARCHITECTURE_DEEP_DIVE.md Section 9 (extensibility patterns)
3. REFERENCE_GUIDE.md Part 13 (integration examples)
4. Development commands in REFERENCE_GUIDE.md

### For Troubleshooting
1. REFERENCE_GUIDE.md Part 7 (error handling)
2. REFERENCE_GUIDE.md Part 11 (troubleshooting)
3. WIKI_SKELETON.md Part 11 (debugging tips)

---

## Document Features

### INDEX.md
- ✅ Quick navigation by role
- ✅ Core concepts summary
- ✅ Architecture at a glance
- ✅ Implementation status
- ✅ Quick start guide
- ✅ Common patterns
- ✅ Resource links

### WIKI_SKELETON.md
- ✅ 12 comprehensive parts
- ✅ Complete system overview
- ✅ All major components
- ✅ Data models and persistence
- ✅ Configuration system
- ✅ Workflows and examples
- ✅ Extension points
- ✅ API reference
- ✅ Development guide
- ✅ Status and roadmap

### ARCHITECTURE_DEEP_DIVE.md
- ✅ Detailed design principles
- ✅ Authority separation model
- ✅ Data flow diagrams
- ✅ Component interactions
- ✅ Boundary contracts
- ✅ Configuration evolution
- ✅ Error handling patterns
- ✅ Extensibility patterns
- ✅ Performance and security
- ✅ Testing architecture

### REFERENCE_GUIDE.md
- ✅ CLI command reference
- ✅ REPL command reference
- ✅ Complete API documentation
- ✅ Schema reference (enums, models)
- ✅ Workflow patterns
- ✅ Configuration file reference
- ✅ Error handling guide
- ✅ Database operations
- ✅ Testing utilities
- ✅ Development commands
- ✅ Troubleshooting guide
- ✅ Performance tuning
- ✅ Integration examples

### INVESTIGATION_REPORT.md
- ✅ Raw source analysis
- ✅ Complete findings summary
- ✅ Recommended structure

---

## Usage Instructions

All documents are stored in `/openwiki/` and ready for:

1. **Integration with wiki system** - Copy to wiki platform
2. **PDF generation** - Convert markdown to PDF
3. **HTML rendering** - Use markdown renderer
4. **Search indexing** - Full-text search across all documents
5. **Version control** - Commit to documentation repository
6. **Cross-referencing** - Links between documents work across files

### File List
- `/openwiki/INDEX.md` - Navigation hub
- `/openwiki/CogniEDA_WIKI_SKELETON.md` - Main wiki (12 parts)
- `/openwiki/CogniEDA_ARCHITECTURE_DEEP_DIVE.md` - Technical design
- `/openwiki/CogniEDA_REFERENCE_GUIDE.md` - API and workflows
- `/openwiki/CogniEDA_INVESTIGATION_REPORT.md` - Investigation findings

---

## Next Steps

### For Wiki Administrators
1. Review all documents for accuracy
2. Customize styling and navigation
3. Set up search indexing
4. Configure version control
5. Plan update cadence with development team

### For Documentation Team
1. Extract diagrams to dedicated image files
2. Add visual process flowcharts
3. Create video tutorials (optional)
4. Build interactive examples (optional)
5. Set up automated documentation builds

### For Development Team
1. Review architecture documentation
2. Validate technical accuracy
3. Update as implementation changes
4. Link from code repositories
5. Integrate with contributor guidelines

### For Users
1. Start with INDEX.md
2. Choose role-based path
3. Bookmark frequently-used sections
4. Provide feedback on clarity
5. Suggest improvements

---

## Quality Assurance Checklist

- ✅ All major components documented
- ✅ All data flows explained
- ✅ All authority boundaries defined
- ✅ All configuration files documented
- ✅ API reference complete
- ✅ Workflows explained
- ✅ Extension points listed
- ✅ Error handling covered
- ✅ Examples provided
- ✅ Navigation clear
- ✅ Role-based paths available
- ✅ Troubleshooting guide included

---

## Maintenance Notes

### Update Triggers
- New feature implementation → Update WIKI_SKELETON.md Part 8
- API changes → Update REFERENCE_GUIDE.md Part 3-4
- Architecture changes → Update ARCHITECTURE_DEEP_DIVE.md
- Configuration changes → Update REFERENCE_GUIDE.md Part 6
- Status changes → Update WIKI_SKELETON.md Part 9
- New extension example → Update REFERENCE_GUIDE.md Part 13

### Review Cycle
- Monthly: Review implementation status
- Quarterly: Deep review with architecture team
- Per-release: Update status and roadmap
- Ad-hoc: Update as issues arise

---

## Summary

A comprehensive five-document wiki skeleton for CogniEDA has been created, totaling **50+ sections** with complete coverage of:

- System architecture and design principles
- All major components and their responsibilities
- Data models and persistence layer
- Configuration system and runtime
- Agent specializations and capabilities
- Execution model and dispatch
- Workflows and use cases
- Extension points and customization
- API reference and schemas
- Development setup and commands
- Troubleshooting and performance tuning
- Integration examples

The wiki is organized for multiple user roles (users, developers, architects, contributors) with clear navigation paths and comprehensive indexing. All documents are ready for integration into a wiki platform, PDF generation, or HTML rendering.

---

**Investigation Date**: 2026-08-14  
**Completion Time**: 17:55:53.157Z  
**Status**: ✅ Complete and ready for deployment


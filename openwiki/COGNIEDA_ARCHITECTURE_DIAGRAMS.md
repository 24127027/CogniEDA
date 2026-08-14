# CogniEDA Architecture Diagram

## System Overview

```mermaid
graph TB
    subgraph Control["🎮 Control Plane"]
        H["👤 Human"]
        P["🧠 Planner<br/>(Cognitive Coordinator)"]
    end

    subgraph Specialist["⚙️ Specialist Plane"]
        DE["📊 Data Explorer<br/>(Dataset Access)"]
        HA["🔬 Hypothesis Analyst<br/>(Scientific Protocol)"]
        GM["🔗 Graph Miner<br/>(Read-Only)"]
    end

    subgraph Authority["✅ Authority Plane"]
        AC["Application<br/>Coordination"]
        GV["Governance<br/>Review"]
        PS["Persistence<br/>SQLite"]
        VR["Validity-Aware<br/>Retrieval"]
    end

    subgraph Infrastructure["🏗️ Infrastructure"]
        LLM["LLM Factory<br/>OpenAI/Google/Anthropic"]
        TOOL["Agent Tooling<br/>Skills & MCP"]
        INFRA["Datasets, DVC,<br/>Persistence"]
    end

    H <-->|human boundary| P
    P -->|route work| AC
    AC -->|dispatch| DE
    AC -->|dispatch| HA
    AC -->|dispatch| GM
    DE -->|result| AC
    HA -->|result| AC
    GM -->|result| AC
    AC -->|validate| GV
    GV -->|decision| AC
    AC <-->|read/write| PS
    PS -->|load state| VR
    VR -->|eligible context| P

    P -.->|agent creation| LLM
    DE -.->|tools| TOOL
    HA -.->|tools| TOOL
    AC -.->|services| INFRA

    style Control fill:#e1f5ff
    style Specialist fill:#fff3e0
    style Authority fill:#f3e5f5
    style Infrastructure fill:#e8f5e9
```

## Research State Lifecycle

```mermaid
stateDiagram-v2
    [*] --> ObjectiveActive: User intent
    
    ObjectiveActive --> PlanProposed: Planner proposes\nObjective + Plan
    PlanProposed --> PlanApproved: Human approves
    
    PlanApproved --> TaskDataExecution: Execute DATA Task
    TaskDataExecution --> DataObservation: Observation recorded
    DataObservation --> TaskDataExecution: More DATA tasks
    
    DataObservation --> TaskScientificExecution: Execute SCIENTIFIC Task
    TaskScientificExecution --> HypothesisFeasibility: HA evaluates feasibility
    
    HypothesisFeasibility --> HypothesisInfeasible: Infeasible
    HypothesisInfeasible --> TaskComplete: Mark as not-testable
    
    HypothesisFeasibility --> HypothesisCreated: Feasible
    HypothesisCreated --> ProtocolExecution: Execute protocol
    ProtocolExecution --> EvidenceGenerated: Observation from execution
    
    EvidenceGenerated --> EvidenceAdmission: Application admits\nEvidence
    EvidenceAdmission --> ProtectedEvaluation: HA evaluates against\nHypothesis
    
    ProtectedEvaluation --> DiscoveryProposal: HA drafts proposal\n(CONFIRMED|INCONCLUSIVE|CONTRADICTED)
    DiscoveryProposal --> GovernanceReview: Governance reviews
    
    GovernanceReview --> DiscoveryRejected: Rejected
    DiscoveryRejected --> TaskComplete: Non-Discovery outcome
    
    GovernanceReview --> DiscoveryAdmitted: Approved
    DiscoveryAdmitted --> ValidityActive: Discovery entered into\nknowledge base
    
    TaskComplete --> SessionEnd: End session
    ValidityActive --> SessionEnd: End session
    
    SessionEnd --> [*]
```

## Message Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI/REPL
    participant App as Application
    participant Planner
    participant PydanticAI as PydanticAI Agent
    participant Dispatcher
    participant Executor as Executor<br/>DataExplorer
    participant DB as Persistence<br/>SQLite

    User->>CLI: Text input or command
    
    alt Command (e.g., /skill, /provider)
        CLI->>App: submit_message()
        App->>App: _handle_command()
        App->>DB: Update config
        App-->>CLI: Status message
    else User query
        CLI->>App: submit_message(text)
        App->>App: build_planner_context()
        App->>DB: Retrieve eligible context
        DB-->>App: SessionFrame + Discoveries + Evidence
        App->>Planner: run(text, context)
        Planner->>PydanticAI: Invoke with context
        PydanticAI->>PydanticAI: Model inference
        
        alt Tool call (e.g., capability dispatch)
            PydanticAI->>Dispatcher: dispatch(ExecutionRequest)
            Dispatcher->>Executor: run(request)
            Executor->>DB: Load dataset/profile
            Executor->>Executor: Execute analysis
            Executor-->>Dispatcher: ExecutionResult
            Dispatcher-->>PydanticAI: Result
            PydanticAI->>PydanticAI: Continue inference
        end
        
        PydanticAI-->>Planner: PlannerResult
        Planner-->>App: PlannerOutput
        App->>App: ConversationHistory.add_turn()
        App->>DB: Persist messages
        App->>App: _present_planner_result()
        App-->>CLI: Message(ASSISTANT, content)
    end
    
    CLI-->>User: Rendered output
```

## Data & State Layering

```mermaid
graph TB
    subgraph Intent["🎯 Research Intent Layer"]
        OBJ["Objective<br/>(what are we investigating?)"]
    end

    subgraph Planning["📋 Planning Layer"]
        PLAN["Plan<br/>(how, structured as DAG)"]
        TASK["Tasks<br/>(semantic work identity)"]
        ASSUME["Assumptions<br/>(provisional beliefs)"]
    end

    subgraph Data["📊 Data State Layer"]
        DPS["DataProfile<br/>(immutable snapshot)"]
        DBIND["Dataset Binding<br/>(hash + reference)"]
    end

    subgraph Scientific["🔬 Scientific Layer"]
        HYP["Hypothesis<br/>(test contract)"]
        PROTO["Protocol<br/>(method + obligations)"]
    end

    subgraph Execution["⚡ Execution Layer"]
        RUN["ExecutionRun<br/>(attempt provenance)"]
        OBS["Observation<br/>(raw result)"]
    end

    subgraph Evidence["✅ Evidence Layer"]
        EVI["Evidence<br/>(admitted observation)"]
        FRAME["AnalysisFrame<br/>(data view used)"]
    end

    subgraph Governance["🏛️ Governance Layer"]
        EVAL["Protected Evaluation<br/>(H vs Evidence)"]
        PROP["DiscoveryProposal<br/>(scoped claim)"]
    end

    subgraph Durable["🎖️ Durable Findings Layer"]
        DISC["Discovery<br/>(admitted claim<br/>with validity)"]
    end

    subgraph Validity["⏰ Validity Layer"]
        VALID["Validity State<br/>(truth vs current-use)"]
    end

    OBJ -->|drives| PLAN
    PLAN -->|owns| TASK
    TASK -->|requires| DPS
    DPS -->|bound to| DBIND
    TASK -->|executed by| RUN
    RUN -->|produces| OBS
    OBS -->|admitted as| EVI
    EVI -->|tagged with| FRAME
    HYP -->|tested against| EVI
    EVI -->|evaluated for| EVAL
    EVAL -->|generates| PROP
    PROP -->|governance→| DISC
    DISC -->|status tracked by| VALID

    style Intent fill:#c8e6c9
    style Planning fill:#bbdefb
    style Data fill:#ffe0b2
    style Scientific fill:#f8bbd0
    style Execution fill:#d1c4e9
    style Evidence fill:#b2dfdb
    style Governance fill:#ffccbc
    style Durable fill:#c5e1a5
    style Validity fill:#e1bee7
```

## Execution Dispatch & Capability Routing

```mermaid
graph LR
    subgraph Request["📥 Execution Request"]
        CAP["Capability:<br/>DATA_ANALYSIS<br/>DATA_PROFILING<br/>DATA_TRANSFORMATION<br/>GRAPH_MINING<br/>HYPOTHESIS_TESTING"]
        INPUT["ExecutorInput<br/>(Task)"]
        CTX["ExecutorContext<br/>(dataset_path,<br/>data_profile_id)"]
    end

    subgraph Registry["📋 Registry"]
        REG["ExecutorRegistry<br/>Capability → Provider<br/>Mapping"]
    end

    subgraph Resolution["🔍 Resolution"]
        RESOLVE["Resolve Provider<br/>for Capability"]
    end

    subgraph Providers["⚙️ Registered Providers"]
        DE_PROV["DataExplorer<br/>↳ DATA_ANALYSIS<br/>↳ DATA_PROFILING<br/>↳ DATA_TRANSFORMATION"]
        HA_PROV["HypothesisAnalyst<br/>↳ HYPOTHESIS_TESTING"]
        GM_PROV["GraphMiner<br/>↳ GRAPH_MINING"]
    end

    subgraph Execution["⚡ Execution"]
        RUN["Provider.run<br/>(request)"]
    end

    subgraph Result["📤 Execution Result"]
        STATUS["Status:<br/>SUCCEEDED<br/>BLOCKED<br/>FAILED"]
        FAIL["Failure Details<br/>(code, message)"]
        LIM["Limitations<br/>(list)"]
    end

    CAP -->|part of| Request
    INPUT -->|part of| Request
    CTX -->|part of| Request
    Request -->|dispatched to| REG
    REG -->|performs| RESOLVE
    RESOLVE -->|matches| DE_PROV
    RESOLVE -->|matches| HA_PROV
    RESOLVE -->|matches| GM_PROV
    DE_PROV -->|provider| RUN
    HA_PROV -->|provider| RUN
    GM_PROV -->|provider| RUN
    RUN -->|generates| Result
    STATUS -->|part of| Result
    FAIL -->|part of| Result
    LIM -->|part of| Result

    style Request fill:#e3f2fd
    style Registry fill:#fff3e0
    style Resolution fill:#f3e5f5
    style Providers fill:#e8f5e9
    style Execution fill:#fce4ec
    style Result fill:#e0f2f1
```

## Authority Boundaries

```mermaid
graph TB
    subgraph Human["👤 Human Authority"]
        INTENT["Intent"]
        APPROVAL["Approval Decisions"]
        CLARIFICATION["Clarification Requests"]
        REJECTION["Rejection"]
    end

    subgraph Planner["🧠 Planner Authority"]
        COORD["Objective Coordination"]
        ROUTING["Routing"]
        REPLANNING["Replanning"]
        PROPOSE_PLAN["Plan & Task Proposals"]
    end

    subgraph DataExp["📊 Data Explorer Authority"]
        DATASET["Dataset Inspection"]
        ANALYSIS["Bounded Data Analysis"]
        PROFILING["Profiling"]
        OBSERVATIONS["Observations & AnalysisFrames"]
    end

    subgraph HypAna["🔬 Hypothesis Analyst Authority"]
        FEASIBILITY["Scientific Feasibility"]
        OPERATIONALIZATION["Hypothesis Operationalization"]
        METHOD["Method Definition"]
        EVAL["Protected Evaluation"]
    end

    subgraph GraphM["🔗 Graph Miner Authority"]
        QUERY["Read-Only Queries"]
        TRAVERSAL["Graph Traversal"]
        METRICS["Metrics Computation"]
    end

    subgraph Governor["🏛️ Governance Authority"]
        REVIEW["Review Proposals"]
        APPROVE["Approve/Reject Discoveries"]
        REQUEST_EVIDENCE["Request More Evidence"]
        CONFLICT_REVIEW["Conflict Review"]
    end

    subgraph AppAuth["✅ Application Authority"]
        VALIDATION["Validate Contracts"]
        ADMISSION["Admit State"]
        TRANSITION["Lifecycle Transitions"]
        PERSIST["Durable Persistence"]
        REPLAY["Replay Safety"]
    end

    Human -->|Input to| Planner
    Planner -->|Consults| DataExp
    Planner -->|Consults| HypAna
    Planner -->|Consults| GraphM
    DataExp -->|Results to| AppAuth
    HypAna -->|Results to| AppAuth
    GraphM -->|Results to| AppAuth
    AppAuth -->|Validates| Governor
    Governor -->|Decisions to| AppAuth
    AppAuth -->|Presentation to| Planner
    Planner -->|Response to| Human

    style Human fill:#c8e6c9
    style Planner fill:#bbdefb
    style DataExp fill:#ffe0b2
    style HypAna fill:#f8bbd0
    style GraphM fill:#d1c4e9
    style Governor fill:#ffccbc
    style AppAuth fill:#b2dfdb
```

## Multi-Session Continuity

```mermaid
sequenceDiagram
    participant S1 as Session 1
    participant DB as Persistence<br/>SQLite
    participant S2 as Session 2

    S1->>S1: Workspace.open(root)
    S1->>DB: Create Objective
    S1->>DB: Create Plan with Tasks
    S1->>DB: Execute DATA tasks
    S1->>DB: Record Observations
    S1->>DB: Admit Evidence
    S1->>S1: Session ends

    Note over DB: State at rest:<br/>- Objective (state, id)<br/>- Plan (DAG, tasks)<br/>- Evidence (tied to DataProfile)<br/>- Task status<br/>- Discovery status<br/>- Validity info

    S2->>S2: Workspace.open(root)
    S2->>DB: Load Objective
    S2->>DB: Load last Plan
    S2->>DB: Query eligible Evidence
    DB-->>S2: Evidence + validity flags
    DB-->>S2: Discoveries + supersession info
    S2->>S2: Reconstruct SessionFrame<br/>(valid context only)
    S2->>S2: Flatten ConversationHistory
    S2->>S2: Planner sees context
    Note over S2: Safe to proceed:<br/>- Intent preserved<br/>- Data state known<br/>- Validity visible<br/>- Invalid findings flagged
    S2->>DB: Continue investigation

    Note over S1,S2: Continuity Properties:<br/>- History of truth preserved<br/>- Current eligibility tracked<br/>- No transcript replay<br/>- Governed state only
```

## Validity Propagation

```mermaid
graph LR
    subgraph V1["DataProfile V1<br/>(ACTIVE)"]
        E1["Evidence E1<br/>(tied to V1)"]
        D1["Discovery D1<br/>(Evidence: E1)"]
    end

    subgraph Change["🔄 Dataset Changes"]
        UPDATE["Dataset updated<br/>New version published"]
    end

    subgraph V2["DataProfile V2<br/>(ACTIVE)"]
        DSUPERSEDE["V1 → SUPERSEDED"]
    end

    subgraph Invalidation["❌ Validity Consequence"]
        TRIGGER["Trigger:<br/>DATA_PROFILE_SUPERSEDED"]
        FLAG_E["Evidence E1<br/>invalidation_reason"]
        FLAG_D["Discovery D1<br/>lifecycle_state: NEEDS_REVIEW<br/>current_use: false"]
    end

    subgraph Retrieval["📖 Session 2 Retrieval"]
        TRUTH["D1 historical truth<br/>= still true-to-record"]
        STATUS["D1 current-use<br/>= false (V1 superseded)"]
        RECOMMEND["Recommendation:<br/>Revalidate with V2"]
    end

    V1 -->|triggers| Change
    Change -->|creates| V2
    V2 -->|implies| Invalidation
    DSUPERSEDE -->|triggers| TRIGGER
    TRIGGER -->|flags| FLAG_E
    TRIGGER -->|flags| FLAG_D
    FLAG_D -->|visible in| Retrieval
    TRUTH -->|returned| Retrieval
    STATUS -->|returned| Retrieval
    RECOMMEND -->|guidance| Retrieval

    style V1 fill:#c8e6c9
    style Change fill:#ffebee
    style V2 fill:#bbdefb
    style Invalidation fill:#ffccbc
    style Retrieval fill:#f3e5f5
```

---

## Key Diagrams Summary

1. **System Overview** — Three cooperating planes (Control, Specialist, Authority) with data flow and infrastructure
2. **Research State Lifecycle** — State machine from Objective through Discovery admission and validity tracking
3. **Message Processing Flow** — Detailed sequence of user input → planner → executor → persistence
4. **Data & State Layering** — Separation of intent, planning, data, scientific, execution, evidence, governance, and durable findings
5. **Execution Dispatch** — Capability routing from request through registry to providers
6. **Authority Boundaries** — Who owns what authority; no participant acquires all powers
7. **Multi-Session Continuity** — How state is preserved and loaded across sessions
8. **Validity Propagation** — How data changes cascade to invalidate dependent findings while preserving historical truth

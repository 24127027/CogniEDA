# Data Explorer (DE) Design Specification - MVP Version

## Overview
This document outlines the design and operational boundaries for the **Data Explorer (DE)** strictly scoped for the MVP release. The system operates within a single asynchronous session. All FCOs (First-Class Objects) are generated and stored in RAM within the Session Frame. 

The DE acts as a bounded execution engine that receives an atomic `Task` from the Planner, utilizes specific tools/code-generation to interact directly with the dataset, and directly instantiates `Evidence` or `DataProfile` objects in RAM based on successful execution.

## Main Responsibilities

**What the DE MUST do:**
*   Act as a stateless specialist invoked directly by the Planner.
*   Take a `Task` (Exploration, Profiling, or Cleaning) as its primary input.
*   Act as the **exclusive** agent permitted to interact directly with the raw dataset.
*   **Handle Initial Profiling:** When requested, scan the dataset to extract minimal profile metrics (rows, columns, data types, distinct values).
*   **Handle User-Managed Cleaning:** When the Planner assigns a basic cleaning `Task` (e.g., handling nulls, type casting based on user approval), the DE must execute the cleaning operations and **automatically re-profile** the dataset.
*   Rely on Pydantic AI's native mechanisms to resolve coding errors (e.g., Pandas syntax errors) internally.
*   Critically evaluate its own tool outputs to ensure they mathematically answer the Task.
*   **Directly create** `Evidence` and `DataProfile` objects in RAM at the final compilation step (bypassing any external Admission Authority).

**What the DE MUST NOT do:**
*   **Must Not clean autonomously:** The DE must only perform cleaning when explicitly instructed by a Planner `Task` following user approval.
*   **Must Not reason or plan high-level tasks:** If a task is poorly formed or impossible, the DE fails and alerts the Planner via execution logs.
*   **Must Not interact with persistent storage:** All outputs are returned to the Planner for the in-memory RAM `SessionFrame`.

## Graph State
The DE operates using LangGraph and Pydantic AI. Its state is built entirely from the Planner's `Task` input and accumulates context throughout the run.

*   **`request` (ExecutionRequest):** Stores the explicit task instructions provided by the Planner.
*   **`raw_data_results` (Any):** Stores the valid data output obtained from successfully executing tools/code, or the profiling metrics obtained after cleaning/profiling.
*   **`execution_logs` (list[str]):** Stores actionable feedback regarding data mismatches or tool failures to send back to the Planner.
*   **`retry_count` (int):** Tracks the number of logical retries to enforce a strict maximum limit.
*   **`final_result` (ExecutionResult | None):** Stores the final payload containing the created FCOs and/or `execution_logs`.

## Node Definition (Original Names Retained)

*   **`route_request`**: Inspects the incoming request and directs the workflow into either the Exploration path or the Profiling/Cleaning path.
*   **`generate_and_execute_code` (Exploration)**: Takes the Task, generates the necessary Python code/tool calls, and executes them against the dataset. Uses Pydantic AI's retry loops for syntax errors.
*   **`evaluate_results` (Exploration)**: Acts as a semantic judge to check if the `raw_data_results` answer the Task. Routes to `compile_result` on success, loops back for minor mismatches, or routes to `handle_failure_and_logs` on fundamental data mismatches.
*   **`execute_profiling_and_cleaning` (Profiling/Cleaning)**:
    *   *If Profiling Task:* Executes baseline profiling to extract the MVP requirements.
    *   *If Cleaning Task:* Safely executes the requested basic cleaning operations on the dataset, and **immediately performs profiling** on the newly cleaned dataset.
*   **`handle_failure_and_logs`**: Compiles tool execution errors and reasons for failure to provide precise context back to the Planner so it can revise the plan.
*   **`compile_result`**: Evaluates the state. If successful, it takes the `raw_data_results`, **directly instantiates** the `Evidence` or `DataProfile` object in RAM, and packages it with any `execution_logs` into the standard response returned to the Planner.

## Workflow Description

**Exploration Path:**
The DE leverages code generation to query and inspect the dataset in `generate_and_execute_code`. Syntax errors are resolved via Pydantic AI. Once successful, `evaluate_results` semantically judges the data output against the Task. If the output matches expectations, the workflow transitions directly to `compile_result`. 

**Profiling and Cleaning Path:**
When a dataset is first loaded, the Planner sends a profiling Task. The DE routes to `execute_profiling_and_cleaning` to extract row counts, columns, and value descriptions. It then transitions directly to `compile_result`. 
If the user requests cleaning, the Planner sends a cleaning Task. The DE hits `execute_profiling_and_cleaning` again, performs the basic data cleaning, automatically runs the profiling logic to capture the new state of the data, and passes the updated metrics to `compile_result`.

**Finalization:**
The `compile_result` node acts as the final terminus. It reads the gathered data from the graph state, directly constructs the required `Evidence` or `DataProfile` object, and hands the complete package back to the Planner.

## LangGraph Diagram

```mermaid
flowchart TD
    START((START)) --> route_request
    
    %% Routing
    route_request -->|Exploration Task| generate_and_execute_code
    route_request -->|Profiling or Cleaning Task| execute_profiling_and_cleaning
    
    %% --- EXPLORATION PATH ---
    generate_and_execute_code --> evaluate_results
    
    evaluate_results -->|Output Answers Task| compile_result
    evaluate_results -->|Logical Mismatch & Under Max Retries| generate_and_execute_code
    evaluate_results -->|Fundamental Data Mismatch / Max Retries| handle_failure_and_logs
    
    %% --- PROFILING & CLEANING PATH ---
    execute_profiling_and_cleaning --> compile_result
    
    %% --- FINALIZATION ---
    handle_failure_and_logs --> compile_result
    compile_result --> END((END))

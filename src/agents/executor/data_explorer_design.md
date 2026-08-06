# Data Explorer (DE) Design Specification

## Overview
This document outlines the finalized design and operational boundaries for the **Data Explorer (DE)**. It serves as a strict reference to ensure the DE adheres to the architectural constraints of the executor dispatch layer and integrates correctly with the Planner and other executors (such as the Hypothesis Analyst). The DE acts as a highly tactical, code-generation execution engine that expects atomic, clearly defined requests and does not engage in high-level logical task planning.

## Main Responsibilities

**What the DE MUST do:**
*   Act as a stateless, bounded specialist invoked strictly via the Executor Dispatcher using capability requests (`data_exploration` or `data_profiling`/`cleaning`).
*   Act as the **exclusive** executor permitted to interact directly with the raw dataset.
*   Receive atomic, simple capability requests from the Planner or HA and generate the exact Python code required to execute them.
*   Rely on Pydantic AI's native retry mechanisms to internally resolve coding errors (e.g., syntax errors, invalid Pandas calls) before semantic evaluation.
*   Critically evaluate its own successful code outputs to ensure they mathematically and structurally answer the expected output defined in the atomic request.
*   Draft immutable `Evidence` or `DataProfile` objects based on successful dataset interactions.
*   Request validation from the Admission Authority for any drafted `Evidence` or `DataProfile` before they can become accepted knowledge.
*   Loop and revise its code if output logically mismatches the expected result (up to a strict maximum retry limit), or loop its cleaning operations if the Admission Authority rejects a proposed `DataProfile`.
*   Log failure reasons when a request is fundamentally flawed (e.g., impossible data constraints) or hits maximum retries, routing these failures back to the caller for plan revision.
*   Return a uniform `ExecutionResult` containing admitted drafts and/or execution logs back to the Dispatcher.

**What the DE MUST NOT do:**
*   **Must Not reason or plan high-level tasks:** The DE assumes the request provided by the Planner/HA is atomic and simple enough to execute via direct code generation. If a task fails, it is the fault of the requester's ambiguity or flawed assumptions.
*   **Must Not autonomously persist authoritative knowledge:** The DE drafts candidate objects but must not write directly to persistent storage. It relies on the Admission Authority for validation.
*   **Must Not formulate scientific hypotheses:** Hypothesis generation and evaluation belong exclusively to the Hypothesis Analyst (HA) and the Planner. 

## Graph State
The DE operates using LangGraph and Pydantic AI. Its state is built entirely from the initial `ExecutionRequest` and accumulates context throughout a single run.

*   **`request` (ExecutionRequest):** Stores the initial atomic capability request (Exploration or Profiling) and session context from the caller (Planner/HA).
*   **`raw_data_results` (Any):** Stores the valid data output obtained from successfully executing the internally generated Python code.
*   **`evidence_draft` (Evidence | None):** Stores the formatted claim drafted from the raw data results before it is sent to the Admission Authority.
*   **`data_profile_draft` (DataProfile | None):** Stores the immutable DataProfile drafted during the dedicated cleaning/profiling path.
*   **`execution_logs` (list[str]):** Stores actionable feedback regarding fundamental data mismatches, request ambiguity, or Admission Authority rejections to send back to the caller.
*   **`retry_count` (int):** Tracks the number of logical retries triggered by `evaluate_results` to enforce a strict maximum retry limit.
*   **`final_result` (ExecutionResult | None):** Stores the final uniform envelope (`ExecutionResult`) containing admitted drafts and/or execution logs.

## Node Definition

*   **`route_request`**: Inspects the incoming atomic request and directs the workflow into either the Evidence Exploration path or the Data Profiling & Cleaning path.
*   **`generate_and_execute_code` (Exploration)**: Takes the atomic request, generates the exact Python code required, and executes it directly against the dataset. Uses Pydantic AI's native retry loops internally to resolve any Python syntax or runtime errors before passing the result forward.
*   **`evaluate_results` (Exploration)**: Acts as a strict semantic judge to check if the successfully executed `raw_data_results` match the expected output defined in the atomic request. It routes to admission on success, triggers a loop to `generate_and_execute_code` for minor logical mismatches, or routes to `handle_failure_and_logs` if it detects a fundamental data mismatch or hits the maximum retry limit (proving the caller's task was flawed).
*   **`draft_and_request_admission` (Exploration)**: Formats the verified `raw_data_results` into an `evidence_draft` and sends an admission request to the Admission Authority.
*   **`execute_profiling_and_cleaning` (Profiling)**: Safely executes atomic cleaning/profiling operations directly on the dataset and invokes the dataset profiler to output a `DataProfile`.
*   **`request_profile_admission` (Profiling)**: Sends the drafted `DataProfile` to the Admission Authority for validation. If rejected, it loops back to `execute_profiling_and_cleaning` to revise the profile based on the rejection logs.
*   **`handle_failure_and_logs`**: Compiles the execution logs, failed code outputs, and reasons for failure (e.g., maximum retries reached, impossible data constraints, rejected admission) to provide precise failure context back to the Planner or HA.
*   **`compile_result`**: Packages any admitted drafts (`Evidence` or `DataProfile`) and/or `execution_logs` into the final `ExecutionResult` to fulfill the uniform Dispatcher contract.

## Workflow Description

The execution run begins when the Dispatcher invokes the DE with an `ExecutionRequest`. The `route_request` node immediately determines if the atomic task requires **Data Exploration (Evidence)** or **Data Profiling/Cleaning (DataProfile)**.

**Exploration Path:**
The DE translates the atomic request directly into Python code and executes it in the `generate_and_execute_code` node. Any pure Python syntax or runtime errors are resolved internally by Pydantic AI's native retry mechanism. Once the code executes successfully, the `evaluate_results` node semantically judges the data output against the caller's expectations. If the data fundamentally contradicts the request (e.g., zero rows found) or max retries are exceeded, it routes to `handle_failure_and_logs` so the caller can revise their task. If the output matches expectations, the DE drafts `Evidence` and requests admission. Rejected Evidence routes to error handling, while accepted Evidence proceeds to final compilation.

**Profiling and Cleaning Path:**
The DE safely executes the cleaning operations and profiles the data in a single mechanical step, drafting a `DataProfile`. It then requests admission. If the Admission Authority rejects the profile, the DE loops back to re-execute and revise its cleaning operations based on the rejection reasons. This loop continues until a valid DataProfile is admitted.

Regardless of the path taken or the success state, the final step is `compile_result`, which packages all drafts and logs into a uniform response returned to the Dispatcher.

## LangGraph Diagram

```mermaid
flowchart TD
    START((START)) --> route_request
    
    %% Routing
    route_request -->|Evidence Request| generate_and_execute_code
    route_request -->|Profiling/Cleaning Request| execute_profiling_and_cleaning
    
    %% --- EXPLORATION PATH ---
    generate_and_execute_code --> evaluate_results
    
    evaluate_results -->|Output Matches Expected| draft_and_request_admission
    evaluate_results -->|Logical Mismatch & Under Max Retries| generate_and_execute_code
    evaluate_results -->|Fundamental Data Mismatch / Max Retries| handle_failure_and_logs
    
    draft_and_request_admission -->|Evidence Admitted| compile_result
    draft_and_request_admission -->|Admission Rejected| handle_failure_and_logs
    
    %% --- PROFILING & CLEANING PATH ---
    execute_profiling_and_cleaning --> request_profile_admission
    
    request_profile_admission -->|Profile Admitted| compile_result
    request_profile_admission -->|Admission Rejected| execute_profiling_and_cleaning
    
    %% --- FINALIZATION ---
    handle_failure_and_logs --> compile_result
    compile_result --> END((END))

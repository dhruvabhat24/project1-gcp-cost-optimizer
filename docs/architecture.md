# Architecture Documentation

## GCP Cost Optimizer for Kubernetes

This document describes the architecture, component responsibilities, data flow, safety boundaries, and local deployment architecture of the GCP Cost Optimizer for Kubernetes.

The architecture is designed around a simple principle:

> Combine infrastructure cost information with actual Kubernetes workload utilization to identify potential resource waste and generate actionable optimization recommendations.

The current implementation is validated in a local, cost-free development environment using Kubernetes, Prometheus, Docker, and Python.

GCP billing data is currently represented through mock data. The architecture allows the cost-data layer to be connected to GCP Billing Export / BigQuery in a future production implementation.

---

# 1. Architecture Overview

The system is implemented as a modular optimization pipeline.

At a high level:

```text
                    +----------------------+
                    |   Cost Data Source   |
                    |                      |
                    | Mock / Future GCP    |
                    | Billing + BigQuery    |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |     Cost Fetcher     |
                    +----------+-----------+
                               |
                               |
          +--------------------+--------------------+
          |                                         |
          v                                         v
+-----------------------+                 +-----------------------+
|      Kubernetes       |                 |      Prometheus       |
|                       |                 |                       |
| Resource Requests     |                 | CPU Utilization       |
| Pod Metadata          |                 | Memory Utilization    |
| Deployment Metadata   |                 |                       |
+-----------+-----------+                 +-----------+-----------+
            |                                         |
            +-------------------+---------------------+
                                |
                                v
                     +-----------------------+
                     |   Metrics Analyzer    |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     | Utilization Analysis  |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     | Over-Provisioning     |
                     | Detection             |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     |    Waste Analysis     |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     | Savings Calculation   |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     | Recommendation Engine |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     |     ActionExecutor    |
                     +-----------+-----------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
          +-------------------+      +-------------------+
          | Kubernetes Action |      | Audit / Reports   |
          +-------------------+      +-------------------+
```

---

# 2. Architectural Goals

The architecture was designed around the following goals.

## 2.1 Separate data collection from optimization

Cost information, Kubernetes resource configuration, and Prometheus utilization are collected independently.

This allows the optimization engine to operate on normalized data rather than being tightly coupled to a specific data source.

---

## 2.2 Support local development

The complete workflow should be testable without requiring paid GCP infrastructure.

The current environment therefore uses:

* Local Kubernetes
* Local Prometheus
* Mock GCP cost data
* Python virtual environment
* Docker Desktop

---

## 2.3 Make optimization recommendations explainable

The system should not simply return a savings number.

Each recommendation should explain:

* Which workload is affected
* How much CPU is requested
* How much CPU is being used
* How much memory is requested
* How much memory is being used
* Why the workload was identified
* What action is recommended
* Estimated monthly savings
* Implementation priority

---

## 2.4 Prevent unsafe Kubernetes modifications

The action layer is separated from the analysis layer.

Recommendations can therefore be generated without modifying Kubernetes.

The ActionExecutor uses dry-run behavior by default and contains additional safeguards around protected namespaces and invalid inputs.

---

## 2.5 Allow future cloud integration

The current cost source is mock data, but the architecture separates cost retrieval from the rest of the optimization pipeline.

This allows a future implementation to replace:

```text
Mock Cost Data
```

with:

```text
GCP Billing Export
        |
        v
    BigQuery
```

without redesigning the complete optimization engine.

---

# 3. System Components

The main application components are:

```text
src/
├── cost_fetcher.py
├── metrics_analyzer.py
├── optimizer_engine.py
└── action_executor.py
```

Each component has a specific responsibility.

---

# 4. Cost Fetcher

## Component

```text
src/cost_fetcher.py
```

## Responsibility

The Cost Fetcher provides cost information to the optimization workflow.

The current implementation uses mock billing data for local development.

The normalized cost information is used by the optimization report and savings analysis.

Typical cost information includes:

* Project ID
* Cost source
* Daily costs
* Seven-day cost
* Estimated monthly cost

---

## Current Architecture

```text
+-------------------+
| Mock Cost Source  |
+---------+---------+
          |
          v
+-------------------+
|   Cost Fetcher    |
+---------+---------+
          |
          v
+-------------------+
| Normalized Cost   |
| Data              |
+-------------------+
```

---

## Future Architecture

A future production implementation can use:

```text
+----------------------+
|   GCP Billing Export |
+----------+-----------+
           |
           v
+----------------------+
|       BigQuery       |
+----------+-----------+
           |
           v
+----------------------+
|     Cost Fetcher     |
+----------+-----------+
           |
           v
+----------------------+
| Normalized Cost Data |
+----------------------+
```

The optimization engine does not need to know whether the source is mock data or GCP billing data.

---

# 5. Kubernetes Layer

Kubernetes provides the workload configuration and resource request information used by the metrics analyzer.

The local environment contains application workloads including:

```text
api-service
batch-worker
high-cpu-app
optimized-service
web-app
```

The analyzer retrieves resource requests configured on these workloads.

Example:

```text
api-service
    CPU request:    1 core
    Memory request: 1 Gi

batch-worker
    CPU request:    1 core
    Memory request: 2 Gi

high-cpu-app
    CPU request:    0.5 core
    Memory request: 500 Mi

optimized-service
    CPU request:    0.05 core
    Memory request: 50 Mi

web-app
    CPU request:    1 core
    Memory request: 2 Gi
```

These requests provide the baseline against which observed usage is compared.

---

# 6. Prometheus Layer

Prometheus provides observed resource utilization.

The local Prometheus deployment runs inside Kubernetes in the `monitoring` namespace.

The application connects to Prometheus through the configured Prometheus URL.

The metrics analyzer uses Prometheus data to retrieve workload-level CPU and memory utilization.

Conceptually:

```text
Kubernetes Workloads
        |
        | metrics
        v
+-------------------+
|    Prometheus     |
+---------+---------+
          |
          | PromQL queries
          v
+-----------------------+
|   Metrics Analyzer    |
+-----------------------+
```

Prometheus connectivity was successfully validated during project testing.

---

# 7. Metrics Analyzer

## Component

```text
src/metrics_analyzer.py
```

## Responsibility

The Metrics Analyzer is responsible for combining Kubernetes configuration with observed Prometheus utilization.

Its main responsibilities are:

1. Connect to Prometheus.
2. Retrieve resource usage.
3. Retrieve Kubernetes resource requests.
4. Calculate CPU utilization.
5. Calculate memory utilization.
6. Calculate average utilization.
7. Identify potential over-provisioning opportunities.

---

# 8. Metrics Data Flow

The metrics analyzer receives two primary inputs.

## Input 1: Resource Requests

From Kubernetes:

```text
CPU Request
Memory Request
```

## Input 2: Actual Usage

From Prometheus:

```text
CPU Usage
Memory Usage
```

These inputs are combined:

```text
              Kubernetes
                  |
                  | Resource Requests
                  v
           +--------------+
           |              |
           |    Metrics   |
           |   Analyzer   |
           |              |
           +--------------+
                  ^
                  |
                  | Actual Usage
                  |
              Prometheus
```

---

# 9. Utilization Calculation

The analyzer calculates utilization using:

```text
Utilization % =
(Actual Usage / Requested Resource) × 100
```

CPU and memory are calculated independently.

For example:

```text
CPU Request = 1.0 core
CPU Usage   = 0.01 core

CPU Utilization =
(0.01 / 1.0) × 100
= 1%
```

The same approach is applied to memory.

The analyzer then calculates an average utilization value that is used by the optimization engine.

---

# 10. Over-Provisioning Detection

The current implementation uses a 30% utilization threshold.

The conceptual decision process is:

```text
                 Workload
                    |
                    v
           Calculate Utilization
                    |
                    v
          Average Utilization
                    |
             +------+------+
             |             |
           < 30%          >= 30%
             |             |
             v             v
       Optimization     Continue
       Opportunity      Monitoring
```

A workload below the threshold is identified as a potential optimization opportunity.

This threshold is a configurable optimization heuristic.

It should not be interpreted as a universal production right-sizing rule.

---

# 11. Optimization Engine

## Component

```text
src/optimizer_engine.py
```

## Responsibility

The Optimization Engine converts metrics analysis into optimization information and recommendations.

Its responsibilities include:

* Waste analysis
* CPU waste calculation
* Memory waste calculation
* Savings estimation
* Recommendation generation
* Priority assignment
* Priority scoring
* Optimization report creation

---

# 12. Waste Analysis

The optimization engine receives the opportunities identified by the Metrics Analyzer.

The basic waste calculations are:

```text
CPU Waste =
max(CPU Request - CPU Usage, 0)
```

and:

```text
Memory Waste =
max(Memory Request - Memory Usage, 0)
```

The output is normalized into an analysis structure.

Example:

```text
Workload:
web-app

CPU Request:
1.0 core

CPU Usage:
0.0001 core

CPU Waste:
~0.9999 cores

Memory Request:
2.0 GB

Memory Usage:
~0.0133 GB

Memory Waste:
~1.9867 GB
```

---

# 13. Savings Calculation

The optimization engine converts resource waste into an estimated monthly savings value.

Conceptually:

```text
CPU Savings
    =
CPU Waste × Monthly CPU Cost

Memory Savings
    =
Memory Waste × Monthly Memory Cost

Total Savings
    =
CPU Savings + Memory Savings
```

The cost assumptions are maintained in the project configuration.

This separation allows cost assumptions to be changed without modifying the core optimization algorithm.

---

# 14. Recommendation Engine

The recommendation engine transforms the waste analysis into actionable recommendations.

Each recommendation contains:

```text
Namespace
Pod Name
Current CPU
Actual CPU
Current Memory
Actual Memory
CPU Utilization
Memory Utilization
Suggested Action
Estimated Savings
Implementation Priority
Priority Score
Reason
```

The recommendations are sorted using the calculated priority score.

---

# 15. Priority Model

The priority model considers utilization and estimated savings.

Conceptually:

```text
Higher Resource Waste
        +
Lower Utilization
        +
Higher Savings
        |
        v
Higher Priority
```

The current implementation uses the following broad priority behavior:

```text
High utilization
    |
    +--> Low priority / monitor

Low utilization
    |
    +--> Right-size resources

Very low utilization
    |
    +--> High priority
```

The model is intended to prioritize review rather than automatically approve infrastructure changes.

---

# 16. ActionExecutor

## Component

```text
src/action_executor.py
```

## Responsibility

The ActionExecutor provides the controlled execution layer between recommendations and Kubernetes.

The architecture intentionally separates:

```text
Recommendation
```

from:

```text
Kubernetes Modification
```

This prevents the optimization engine from directly modifying workloads.

---

# 17. ActionExecutor Flow

```text
Recommendation
       |
       v
+----------------------+
|   ActionExecutor     |
+----------+-----------+
           |
           v
    Validate Request
           |
           v
   Check Protected NS
           |
           v
    Resolve Workload
           |
           v
   Generate Kubernetes
        Command
           |
           v
       Dry Run
           |
      +----+----+
      |         |
      v         v
   Audit      Output
    Log
```

---

# 18. Pod to Deployment Resolution

Optimization recommendations can contain Pod names.

Kubernetes scaling and resource updates are performed against Deployments.

The ActionExecutor therefore resolves the ownership hierarchy.

```text
Pod
 |
 | ownerReference
 v
ReplicaSet
 |
 | ownerReference
 v
Deployment
```

For example:

```text
web-app-79bc9f6b6c-td285
            |
            v
web-app-79bc9f6b6c
            |
            v
web-app
```

The project successfully validated this resolution against the local Kubernetes cluster.

---

# 19. Container Resolution

A Deployment may contain one or more containers.

The ActionExecutor identifies the appropriate application container before generating a resource patch.

For the local workloads, the application container names were validated:

```text
api-service
batch-worker
high-cpu-app
optimized-service
web-app
```

This helps prevent a resource update from targeting the wrong container.

---

# 20. Dry-Run Execution

Dry-run mode is enabled by default.

Instead of applying a Kubernetes operation, the executor prints the command that would be executed.

Example:

```text
[DRY-RUN] Would execute:

kubectl scale deployment web-app --replicas=3 -n default
```

The method returns success for a valid simulated operation while recording the action.

This provides a safe demonstration environment.

---

# 21. Protected Namespace Controls

The ActionExecutor prevents modifications to protected Kubernetes namespaces.

Protected namespaces include:

```text
kube-system
kube-public
kube-node-lease
```

Example:

```text
Refusing to scale protected namespace: kube-system
```

The operation returns failure instead of generating an action.

This protects core Kubernetes infrastructure from the optimization workflow.

---

# 22. Input Validation

The ActionExecutor validates action parameters.

For scaling operations, the replica count must be at least one.

Example invalid input:

```text
replicas = 0
```

Result:

```text
ValueError:
Replica count must be at least 1
```

This prevents invalid scaling commands from being generated.

---

# 23. Audit Logging Architecture

Every action generated by the ActionExecutor is recorded.

The audit record contains information such as:

```text
Timestamp
Namespace
Resource
Action
Old Value
New Value
Dry-Run State
```

Example:

```text
{
    "timestamp": "...",
    "namespace": "default",
    "resource": "web-app",
    "action": "right-size",
    "old_value": "unknown",
    "new_value": {
        "cpu": "0.010",
        "memory": "0.020Gi"
    },
    "dry_run": true
}
```

The audit log provides traceability for both simulated and future real execution.

---

# 24. Reporting Layer

The system provides two main forms of reporting.

## Optimization Report

The Optimization Engine generates a detailed report containing:

* Cost information
* Optimization opportunity count
* Priority breakdown
* Estimated savings
* Detailed recommendations

---

## Weekly Report

The ActionExecutor can generate a concise weekly summary containing:

* Recommendation count
* Estimated monthly savings
* Individual recommendation summaries

Example:

```text
Kubernetes Cost Optimizer - Weekly Summary
==================================================
Recommendations: 2
Estimated monthly savings: ₹83.05

- default/web-app: Right-size CPU and memory | ₹31.95/month
- default/batch-worker: Consider Spot instance | ₹51.10/month
```

---

# 25. Local Infrastructure Architecture

The project was developed and validated locally.

The environment consists of:

```text
+-------------------------------------------+
|              Developer Machine            |
|                                           |
|  Windows + Docker Desktop                 |
|                                           |
|  +-------------------------------------+  |
|  |          Local Kubernetes            |  |
|  |                                     |  |
|  |  +-------------+                    |  |
|  |  | Application |                    |  |
|  |  | Workloads   |                    |  |
|  |  +------+------+                    |  |
|  |         |                           |  |
|  |         v                           |  |
|  |  +-------------+                    |  |
|  |  | Prometheus  |                    |  |
|  |  +-------------+                    |  |
|  |                                     |  |
|  +-------------------------------------+  |
|                                           |
|  +-------------------------------------+  |
|  |       Python Optimization Engine    |  |
|  |                                     |  |
|  | Cost Fetcher                        |  |
|  | Metrics Analyzer                    |  |
|  | Optimization Engine                |  |
|  | ActionExecutor                     |  |
|  +-------------------------------------+  |
|                                           |
+-------------------------------------------+
```

---

# 26. Kubernetes Namespace Architecture

The local Kubernetes environment contains several namespaces.

Application workloads run in the `default` namespace.

Prometheus runs in the `monitoring` namespace.

Kubernetes system components run in `kube-system`.

Conceptually:

```text
Kubernetes Cluster
|
+-- default
|   |
|   +-- api-service
|   +-- batch-worker
|   +-- high-cpu-app
|   +-- optimized-service
|   +-- web-app
|
+-- monitoring
|   |
|   +-- prometheus
|
+-- kube-system
    |
    +-- Kubernetes control-plane components
```

The ActionExecutor prevents automated modification of protected system namespaces.

---

# 27. Service and Monitoring Relationship

The application workloads run inside Kubernetes while Prometheus observes their resource utilization.

The relationship can be represented as:

```text
+----------------------+
| Kubernetes Workloads |
+----------+-----------+
           |
           | Resource Metrics
           v
+----------------------+
|     Prometheus       |
+----------+-----------+
           |
           | PromQL
           v
+----------------------+
|   Metrics Analyzer   |
+----------------------+
```

This creates the observability foundation for resource optimization.

---

# 28. End-to-End Data Flow

The complete data flow is:

```text
                    COST DATA
                       |
                       v
                +-------------+
                | Cost Fetcher|
                +------+------+
                       |
                       |
                       |
KUBERNETES             |             PROMETHEUS
Resource Requests      |             Usage Metrics
       |               |                  |
       |               |                  |
       +---------------+------------------+
                       |
                       v
               +---------------+
               |    Metrics    |
               |    Analyzer   |
               +-------+-------+
                       |
                       v
               +---------------+
               | Utilization   |
               | Calculation   |
               +-------+-------+
                       |
                       v
               +---------------+
               | Over-          |
               | Provisioning   |
               | Detection      |
               +-------+-------+
                       |
                       v
               +---------------+
               | Waste Analysis |
               +-------+-------+
                       |
                       v
               +---------------+
               | Savings        |
               | Calculation    |
               +-------+-------+
                       |
                       v
               +---------------+
               | Recommendation |
               | Engine         |
               +-------+-------+
                       |
                       v
               +---------------+
               | ActionExecutor |
               +-------+-------+
                       |
              +--------+--------+
              |                 |
              v                 v
       Kubernetes          Audit / Reports
       Dry-Run Actions
```

---

# 29. Data Contracts Between Components

The architecture uses structured Python dictionaries and lists to pass normalized information between components.

## Resource Usage

Conceptually:

```text
{
    "namespace/pod": {
        "cpu": <actual CPU usage>,
        "memory": <actual memory usage>
    }
}
```

---

## Resource Requests

Conceptually:

```text
{
    "namespace/pod": {
        "cpu": <requested CPU>,
        "memory": <requested memory>
    }
}
```

---

## Optimization Opportunity

Conceptually:

```text
{
    "namespace": "...",
    "name": "...",
    "cpu_request": ...,
    "memory_request": ...,
    "cpu_usage": ...,
    "memory_usage": ...,
    "cpu_utilization_percent": ...,
    "memory_utilization_percent": ...,
    "average_utilization_percent": ...,
    "reason": "..."
}
```

---

## Recommendation

Conceptually:

```text
{
    "namespace": "...",
    "pod_name": "...",
    "current_cpu_cores": ...,
    "actual_cpu_cores": ...,
    "current_memory_gb": ...,
    "actual_memory_gb": ...,
    "cpu_utilization_percent": ...,
    "memory_utilization_percent": ...,
    "suggested_action": "...",
    "estimated_monthly_savings_inr": ...,
    "implementation_priority": "...",
    "priority_score": ...,
    "reason": "..."
}
```

These normalized structures keep the individual components loosely coupled.

---

# 30. Component Dependency Model

The logical dependency relationship is:

```text
cost_fetcher
      |
      v
optimization_engine

metrics_analyzer
      |
      v
optimization_engine
      |
      v
action_executor
```

More specifically:

```text
CostFetcher
    |
    +----------------------+
                           |
MetricsAnalyzer ---------> OptimizationEngine
                                  |
                                  v
                           ActionExecutor
```

The Metrics Analyzer is responsible for collecting and preparing utilization information.

The Optimization Engine is responsible for interpreting that information.

The ActionExecutor is responsible for controlled infrastructure operations.

---

# 31. Separation of Responsibilities

The architecture intentionally separates responsibilities.

| Component           | Primary Responsibility                    |
| -------------------- | ----------------------------------------- |
| Cost Fetcher         | Cost data collection                      |
| Kubernetes           | Resource configuration and workload state |
| Prometheus           | Observed workload metrics                 |
| Metrics Analyzer     | Usage and utilization analysis            |
| Optimization Engine  | Waste, savings, and recommendations       |
| ActionExecutor       | Controlled Kubernetes operations          |
| Audit Layer          | Action traceability                       |
| Reporting Layer      | Human-readable optimization results       |

This separation improves maintainability and makes individual components easier to test.

---

# 32. Local vs Production Architecture

## Current Local Architecture

```text
Mock Cost Data
      |
      v
Python Application
      |
      +-------------------+
      |                   |
      v                   v
Kubernetes           Prometheus
      |                   |
      +---------+---------+
                |
                v
       Optimization Engine
                |
                v
         ActionExecutor
            Dry-Run
```

---

## Future Production Architecture

```text
GCP Billing Export
        |
        v
    BigQuery
        |
        v
   Cost Fetcher
        |
        +--------------------+
        |                    |
        v                    v
   Kubernetes           Prometheus
        |                    |
        +---------+----------+
                  |
                  v
        Optimization Engine
                  |
                  v
        Policy / Approval Layer
                  |
                  v
           ActionExecutor
                  |
          +-------+-------+
          |               |
          v               v
     Kubernetes        Audit Logs
```

The future architecture introduces additional production controls such as historical data, policy validation, approval workflows, and potentially automated execution.

---

# 33. Security and Safety Considerations

The current project is primarily a local demonstration system, but the architecture considers several infrastructure safety concerns.

## Dry-Run by Default

The executor does not modify Kubernetes resources during normal development.

## Namespace Protection

System namespaces are protected.

## Input Validation

Invalid scaling values are rejected.

## Separation of Analysis and Execution

The recommendation engine does not directly modify Kubernetes.

## Auditability

Actions are recorded.

These controls reduce the risk of unintended infrastructure modifications.

---

# 34. Scalability Considerations

The current implementation is designed for a local demonstration environment.

For a larger production implementation, the architecture could be extended with:

* Multiple Kubernetes clusters
* Centralized Prometheus
* Historical metrics storage
* GCP Billing Export
* BigQuery
* Scheduled analysis
* Distributed workers
* Persistent recommendation storage
* Centralized audit logging
* Approval workflows
* Web dashboard

A multi-cluster architecture could look like:

```text
                +----------------+
                |  Cost / Billing|
                +-------+--------+
                        |
                        v
                 +-------------+
                 | Optimization|
                 |   Service   |
                 +------+------+
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
      Cluster A     Cluster B     Cluster C
          |             |             |
      Prometheus    Prometheus    Prometheus
          |             |             |
          +-------------+-------------+
                        |
                        v
                Recommendations
```

---

# 35. Architectural Trade-offs

Several deliberate trade-offs were made during implementation.

## Local Kubernetes Instead of GCP Kubernetes

### Advantage

* No cloud cost
* Easy development
* Fast iteration
* Safe testing

### Trade-off

* Does not reproduce all production GCP behavior
* Cost data is simulated

---

## Mock Billing Data

### Advantage

* No GCP billing setup required
* No billing permissions required
* Reproducible local testing

### Trade-off

* Savings are estimates
* No direct relationship to real GCP billing

---

## Dry-Run Actions

### Advantage

* Prevents accidental modifications
* Safe for development
* Easy to demonstrate

### Trade-off

* Does not validate the complete real-world mutation path

---

## Current Utilization Window

### Advantage

* Simple
* Fast
* Easy to understand

### Trade-off

* Instantaneous or short-window usage may not represent workload behavior over longer periods
* Production right-sizing should use historical and percentile-based analysis

---

# 36. Architecture Validation

The architecture was validated through component-level testing.

The following integration points were successfully demonstrated:

```text
Python
   |
   v
Prometheus Connectivity
   |
   v
Resource Usage
   |
   v
Kubernetes Resource Requests
   |
   v
Utilization Analysis
   |
   v
Optimization Opportunities
   |
   v
Waste Analysis
   |
   v
Savings Calculation
   |
   v
Recommendations
   |
   v
ActionExecutor
   |
   v
Dry-Run Kubernetes Actions
   |
   v
Audit / Reports
```

Validated components include:

* Prometheus connectivity
* Kubernetes resource requests
* Prometheus resource usage
* Utilization calculation
* Over-provisioning detection
* Waste analysis
* Savings calculation
* Recommendation generation
* Optimization report generation
* ActionExecutor import and initialization
* Deployment resolution
* Dry-run scaling
* Protected namespace handling
* Invalid replica validation
* Audit logging
* Resource patch generation

---

# 37. Architecture Summary

The architecture combines three primary information sources:

```text
Cost
 |
 +--> What are we paying for?

Kubernetes Requests
 |
 +--> What resources have we allocated?

Prometheus Usage
 |
 +--> What resources are workloads actually consuming?
```

These inputs are combined to answer:

```text
What resources are being wasted?
        |
        v
How much could potentially be optimized?
        |
        v
Which workloads should be prioritized?
        |
        v
What action could be taken safely?
```

The resulting architecture is:

```text
Cost
  +
Kubernetes Configuration
  +
Prometheus Utilization
        |
        v
Metrics Analysis
        |
        v
Waste Detection
        |
        v
Savings Estimation
        |
        v
Prioritized Recommendations
        |
        v
Safe Kubernetes Actions
        |
        v
Audit + Reporting
```

The current implementation provides a complete local demonstration of this architecture while keeping the cost source and execution layer modular enough for future production integration.
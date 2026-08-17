# GCP Cost Optimizer for Kubernetes

A Kubernetes-focused cost optimization engine that combines cloud cost analysis, Prometheus resource utilization metrics, workload right-sizing analysis, savings estimation, prioritized recommendations, and safe Kubernetes actions.

---

## Project Overview

The GCP Cost Optimizer for Kubernetes is a DevOps/Cloud engineering project designed to identify Kubernetes workloads that are requesting significantly more CPU and memory resources than they actually consume.

The system combines:

- Kubernetes workload resource requests
- Observed CPU and memory utilization from Prometheus
- Cloud cost data
- Resource waste analysis
- Estimated cost savings
- Prioritized optimization recommendations
- Safety-controlled Kubernetes actions
- Audit logging
- Optimization reports

The project is currently designed and validated as a **local, cost-free demonstration environment** using Docker, Kubernetes, and Prometheus.

The GCP billing integration is represented through mock billing data during local development. The cost-fetching layer is structured so that it can be connected to GCP Billing Export / BigQuery in a production environment.

---

## Problem Statement

Kubernetes workloads are often configured with CPU and memory requests that are larger than what the workloads actually consume.

This can lead to:

- Underutilized compute resources
- Inefficient cluster capacity utilization
- Unnecessary infrastructure allocation
- Difficulty identifying workloads suitable for right-sizing
- Manual effort when reviewing resource allocation and cost

Traditional cost analysis focuses primarily on **how much infrastructure costs**. However, cost optimization also requires understanding **how efficiently that infrastructure is being used**.

This project addresses that gap by correlating cost information with actual Kubernetes workload utilization.

The system analyzes:

- CPU resource requests
- Memory resource requests
- Actual CPU utilization
- Actual memory utilization
- Workload-level resource waste
- Estimated optimization opportunities

The resulting analysis is converted into prioritized recommendations that can be reviewed before any Kubernetes changes are made.

---

## Solution

This project implements a modular optimization pipeline that:

1. Retrieves cloud cost information.
2. Collects observed Kubernetes CPU and memory utilization from Prometheus.
3. Retrieves Kubernetes resource requests.
4. Calculates resource utilization percentages.
5. Identifies potentially over-provisioned workloads.
6. Calculates CPU and memory waste.
7. Estimates potential monthly savings.
8. Assigns optimization priorities.
9. Generates actionable recommendations.
10. Provides a safety-controlled Kubernetes execution layer.
11. Records actions through an audit log.
12. Generates optimization and weekly reports.

The system is intentionally designed with a **dry-run execution mode enabled by default**, allowing recommendations to be demonstrated without modifying the Kubernetes cluster.

---

## Key Engineering Highlights

- Prometheus-driven Kubernetes resource utilization analysis
- CPU and memory right-sizing recommendations
- Kubernetes resource waste detection
- Estimated monthly savings calculation
- Priority-based optimization recommendations
- Protected Kubernetes namespace safeguards
- Pod → ReplicaSet → Deployment resource resolution
- Dry-run Kubernetes action execution
- Action audit logging
- Automated optimization reports
- Modular Python architecture
- Local Docker, Kubernetes, and Prometheus development environment

---

## Current Implementation Status

| Component | Status |
|---|---|
| Python application | Implemented |
| Kubernetes cluster | Local Kubernetes cluster |
| Sample workloads | Running |
| Prometheus | Running locally |
| Prometheus metrics collection | Validated |
| Kubernetes resource requests | Validated |
| Utilization analysis | Validated |
| Over-provisioning detection | Validated |
| Waste analysis | Validated |
| Savings calculation | Validated |
| Recommendation engine | Validated |
| Optimization report | Validated |
| ActionExecutor | Validated |
| Pod → Deployment resolution | Validated |
| Dry-run Kubernetes execution | Validated |
| GCP billing data | Mock data for local development |
| Production GCP deployment | Future enhancement |
| Web dashboard | Future enhancement |

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Core application and optimization logic |
| Kubernetes | Workload orchestration and resource management |
| Docker | Local container runtime |
| Prometheus | CPU and memory utilization monitoring |
| GCP / BigQuery | Target cloud cost-data integration |
| kubectl | Kubernetes management and action execution |
| Git | Source control and version management |

---

# Architecture

The system follows a modular architecture where cloud cost information, Kubernetes resource configuration, and Prometheus utilization data are combined to produce optimization recommendations.

## High-Level Architecture

The detailed visual architecture diagram will be added to the documentation as part of the project architecture documentation.

## Core Architecture Flow

```text
                         GCP / BigQuery
                       Billing Export
                              |
                              |
                              v
                       +--------------+
                       | Cost Fetcher |
                       +------+-------+
                              |
                              |
          +-------------------+-------------------+
          |                                       |
          v                                       v
 +-------------------+                   +-------------------+
 |    Kubernetes     |                   |    Prometheus     |
 |      Cluster      |                   |      Server       |
 |                   |                   |                   |
 | Resource Requests |                   | CPU / Memory      |
 | Workload Metadata |                   | Utilization       |
 +---------+---------+                   +---------+---------+
           |                                       |
           +-------------------+-------------------+
                               |
                               v
                    +-----------------------+
                    |   Metrics Analyzer    |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |  Optimization Engine  |
                    +-----------+-----------+
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
        +------------------+          +-------------------+
        |  Waste Analysis  |          | Savings Estimate  |
        +--------+---------+          +---------+---------+
                 |                              |
                 +--------------+---------------+
                                |
                                v
                    +-----------------------+
                    |   Recommendations     |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |    ActionExecutor     |
                    +-----------+-----------+
                                |
                   +------------+------------+
                   |                         |
                   v                         v
          +----------------+        +----------------+
          |   Kubernetes   |        | Audit/Reports  |
          |    Actions     |        |                |
          +----------------+        +----------------+
```
The GCP / BigQuery component is currently represented by mock cost data in the local implementation. Kubernetes and Prometheus are running locally.

---
# How the System Works

The system follows a sequential optimization workflow that combines cost information, Kubernetes configuration, and observed workload metrics.

The overall workflow is:

```text
Cost Data
    |
    v
Cost Fetcher
    |
    +-----------------------------+
    |                             |
    v                             v
Kubernetes                    Prometheus
Resource Requests             Resource Usage
    |                             |
    +-------------+---------------+
                  |
                  v
          Metrics Analyzer
                  |
                  v
        Utilization Analysis
                  |
                  v
       Over-Provisioning Detection
                  |
                  v
           Waste Analysis
                  |
                  v
        Savings Estimation
                  |
                  v
        Recommendation Engine
                  |
                  v
           ActionExecutor
             /        \
            v          v
     Kubernetes      Reports
       Actions       & Audit
```

## 1. Cost Collection

The cost-fetching layer is responsible for obtaining the cost information used by the optimization engine.

In the current local implementation, the project uses **mock billing data** rather than connecting to a live GCP billing account.

This approach allows the complete optimization workflow to be developed and tested without requiring paid GCP infrastructure.

The cost data contains information such as:

* GCP project identifier
* Cost source
* Daily cost information
* Seven-day total cost
* Estimated monthly cost

Example result from the local implementation:

```text
GCP Project: demo-project
Cost Source: mock

7-Day GCP Cost: ₹1,030.80
Estimated Monthly GCP Cost: ₹4,417.71
```

These values are **demonstration values generated by the local cost-fetching implementation** and should not be interpreted as actual GCP billing charges.

### Future GCP Integration

The cost-fetching layer is designed so that the mock cost source can eventually be replaced or extended with a production GCP billing data source.

A potential production flow would be:

```text
GCP Billing Export
        |
        v
    BigQuery
        |
        v
    Cost Fetcher
        |
        v
Normalized Cost Data
```

This keeps the cost source separate from the optimization logic.

---

## 2. Kubernetes Resource Collection

The metrics analyzer retrieves the resource requests configured for Kubernetes workloads.

For the application workloads used in the local environment, the configured requests include CPU and memory resources.

Example:

| Workload          | CPU Request | Memory Request |
| ----------------- | ----------: | -------------: |
| api-service       |   1.0 cores |         1.0 Gi |
| batch-worker      |   1.0 cores |         2.0 Gi |
| high-cpu-app      |   0.5 cores |         500 Mi |
| optimized-service |  0.05 cores |          50 Mi |
| web-app           |   1.0 cores |         2.0 Gi |

These values represent the resources requested by the workloads from Kubernetes.

The system uses these requests as the baseline for comparing actual workload utilization.

---

## 3. Prometheus Metrics Collection

Prometheus is used to collect observed CPU and memory utilization from the local Kubernetes workloads.

The metrics analyzer connects to the local Prometheus server and queries the metrics required for the optimization analysis.

Prometheus connectivity was validated successfully during testing.

Example connectivity test:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); print(a.connect_to_prometheus())"
```

Result:

```text
True
```

The analyzer was also successfully tested for retrieving workload-level resource usage.

Example workloads returned by the analyzer included:

```text
default/api-service
default/batch-worker
default/high-cpu-app
default/optimized-service
default/web-app
```

Because these values are collected from currently running workloads, the exact usage values can change between executions.

---

## 4. Resource Utilization Analysis

After collecting resource usage and resource requests, the metrics analyzer calculates CPU and memory utilization percentages.

The basic calculation is:

```text
Utilization % = (Actual Usage / Resource Request) × 100
```

CPU and memory are evaluated independently.

For example, if a workload has:

```text
CPU Request = 1.0 core
Actual CPU Usage = 0.01 core
```

then:

```text
CPU Utilization =
(0.01 / 1.0) × 100
= 1%
```

The same calculation is performed for memory.

The analyzer then combines the CPU and memory utilization values into an average utilization value used by the optimization logic.

---

## 5. Over-Provisioning Detection

The system identifies workloads that may be over-provisioned based on their observed utilization.

The current implementation uses a **30% utilization threshold**.

Conceptually:

```text
Average Utilization
        |
        v
   Is it < 30%?
      /     \
    Yes      No
     |        |
     v        v
Potential    No immediate
Optimization optimization
Opportunity  recommendation
```

A workload below the threshold is flagged as a potential optimization opportunity.

The system does **not** automatically assume that the workload can safely be reduced to its instantaneous usage.

In a production environment, right-sizing decisions should also consider:

* Historical utilization
* Peak usage
* CPU and memory percentiles
* Traffic patterns
* Workload behavior
* Service-level objectives
* Application performance requirements
* Safety margins

Therefore, the current implementation should be understood as an **optimization recommendation system**, rather than an automatic resource-sizing authority.

---

## 6. Waste Analysis

Once potential optimization opportunities are identified, the optimization engine calculates the unused portion of the requested resources.

CPU waste is calculated as:

```text
CPU Waste =
max(CPU Request - Actual CPU Usage, 0)
```

Memory waste is calculated as:

```text
Memory Waste =
max(Memory Request - Actual Memory Usage, 0)
```

For example:

```text
CPU Request: 1.0 core
Actual Usage: 0.002 core

CPU Waste:
1.0 - 0.002
= 0.998 cores
```

Similarly:

```text
Memory Request: 2.0 GB
Actual Usage: 0.001 GB

Memory Waste:
2.0 - 0.001
= 1.999 GB
```

The calculated waste values are then passed to the savings calculation stage.

---

## 7. Savings Estimation

The optimization engine estimates potential monthly savings based on the calculated CPU and memory waste.

The calculation uses configurable cost assumptions defined by the project configuration.

Conceptually:

```text
CPU Savings
    =
CPU Waste × Monthly CPU Cost

Memory Savings
    =
Memory Waste × Monthly Memory Cost

Total Estimated Savings
    =
CPU Savings + Memory Savings
```

The result is an estimated monthly optimization opportunity.

For example, during testing:

```text
Estimated monthly savings:
₹122.95
```

This figure represents the sum of the estimated savings associated with the identified local optimization opportunities.

It is important to distinguish this from actual GCP billing savings.

Actual savings in a production environment would depend on how resource right-sizing affects:

* Node utilization
* Cluster capacity
* Autoscaling
* Pod scheduling
* GCP machine types
* Pricing models
* Discounts
* Spot/Preemptible capacity
* Other infrastructure costs

---

## 8. Recommendation Generation

The optimization engine converts the waste analysis into actionable recommendations.

Each recommendation contains information such as:

* Namespace
* Pod name
* Current CPU request
* Actual CPU usage
* Current memory request
* Actual memory usage
* CPU utilization percentage
* Memory utilization percentage
* Suggested action
* Estimated monthly savings
* Implementation priority
* Priority score
* Reason for recommendation

Example:

```text
Pod:
default/web-app-79bc9f6b6c-td285

CPU:
0.0001 / 1.0000 cores

Memory:
0.0133 / 2.0000 GB

CPU Utilization:
~0.0%

Memory Utilization:
~0.7%

Suggested Action:
Right-size CPU and memory requests based on observed utilization

Estimated Monthly Savings:
₹31.95

Priority:
High
```

The recommendations are sorted according to their calculated priority score.

---

## 9. Priority Scoring

The optimization engine assigns a priority score to recommendations.

The score considers:

* Resource utilization
* Estimated savings
* Degree of potential waste

Conceptually:

```text
Lower utilization
        +
Higher estimated savings
        +
Higher resource waste
        |
        v
Higher priority score
```

This allows the system to surface workloads that may provide greater optimization value.

The priority score is bounded to prevent it from exceeding the configured maximum score.

---

## 10. Special Handling for Batch Workloads

The optimization engine contains additional logic for batch workloads.

For the `batch-worker` workload, the recommendation can include:

```text
Right-size resources and consider Spot instance/node pool
```

This is based on the fact that batch workloads may be suitable for lower-cost compute capacity when their workload characteristics allow interruption or delayed execution.

This recommendation is presented as an optimization consideration rather than an automatic migration.

---

## 11. Optimization Report Generation

After recommendations are generated, the system can create a consolidated optimization report.

The report includes:

* Project information
* Cost source
* Seven-day cost
* Estimated monthly cost
* Number of optimization opportunities
* High-priority recommendations
* Medium-priority recommendations
* Low-priority recommendations
* Estimated monthly savings
* Detailed workload recommendations

Example summary:

```text
GCP Project: demo-project
Cost Source: mock

7-Day GCP Cost: ₹1,030.80
Estimated Monthly GCP Cost: ₹4,417.71

Optimization Opportunities: 5
High Priority: 5
Medium Priority: 0
Low Priority: 0

Estimated Monthly Savings: ₹122.95
```

---

## 12. Safe Action Execution

The final stage of the pipeline is the `ActionExecutor`.

The purpose of this component is to translate approved recommendations into Kubernetes actions while providing safety controls.

The execution layer supports operations such as:

* Scaling deployments
* Updating resource requests and limits
* Generating Kubernetes commands
* Recording actions in an audit log

The project uses **dry-run mode by default**.

Example:

```text
[DRY-RUN] Would execute:
kubectl scale deployment web-app --replicas=3 -n default
```

The command is displayed and logged instead of being applied to the cluster.

This provides a safe way to demonstrate the automation workflow without accidentally modifying workloads.

---

# Safety Controls

The ActionExecutor contains several safety mechanisms.

## Protected Namespaces

Critical Kubernetes namespaces are protected from automated modifications.

Protected namespaces include:

```text
kube-system
kube-public
kube-node-lease
```

Example test:

```text
Refusing to scale protected namespace: kube-system
RESULT: False
```

This prevents the optimization engine from accidentally modifying core Kubernetes components.

---

## Replica Validation

The executor validates replica counts before generating a scaling operation.

Invalid values such as:

```text
0
```

are rejected.

Example:

```text
ValueError:
Replica count must be at least 1
```

---

## Pod to Deployment Resolution

Optimization recommendations can contain Pod names, while scaling and resource modifications are performed against Deployments.

The ActionExecutor therefore resolves the workload hierarchy:

```text
Pod
 |
 v
ReplicaSet
 |
 v
Deployment
```

Example:

```text
Pod:
web-app-79bc9f6b6c-td285

        |
        v

ReplicaSet:
web-app-79bc9f6b6c

        |
        v

Deployment:
web-app
```

This behavior was validated successfully against the local Kubernetes cluster.

---

## Container Resolution

Before generating a resource patch, the executor identifies the correct container in the Deployment.

For example:

```text
Deployment:
web-app

Container:
web-app
```

The same validation was performed for the other application deployments:

```text
api-service
optimized-service
high-cpu-app
batch-worker
```

This helps ensure that resource modifications target the intended application container.

---

# Audit Logging

The ActionExecutor records every simulated or executed action.

Example audit entry:

```text
{
    "timestamp": "2026-08-17T04:29:49.802716+00:00",
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

The audit information provides traceability for optimization operations.

A weekly report can also be generated from recommendation data.

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

# End-to-End Optimization Flow

The complete local workflow can be summarized as:

```text
                         +----------------+
                         |  Mock Cost Data |
                         +-------+--------+
                                 |
                                 v
                         +---------------+
                         | Cost Fetcher  |
                         +-------+-------+
                                 |
                                 |
              +------------------+------------------+
              |                                     |
              v                                     v
      +---------------+                     +---------------+
      |  Kubernetes   |                     |  Prometheus   |
      |    Requests   |                     |     Usage     |
      +-------+-------+                     +-------+-------+
              |                                     |
              +------------------+------------------+
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
                     |  Savings Calculation  |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     | Recommendations       |
                     | + Priority Score      |
                     +-----------+-----------+
                                 |
                                 v
                     +-----------------------+
                     |    ActionExecutor     |
                     +-----------+-----------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
             +-------------+          +---------------+
             | Kubernetes  |          | Audit/Reports |
             | Dry-Run     |          |               |
             +-------------+          +---------------+
```

This represents the workflow currently implemented and validated in the local development environment.
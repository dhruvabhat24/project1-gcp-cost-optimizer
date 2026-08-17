# Deployment and Setup Guide

## GCP Cost Optimizer for Kubernetes

This document explains how to set up and run the GCP Cost Optimizer for Kubernetes in the local development environment.

The current project is designed as a **local, cost-free demonstration environment** using Docker Desktop, Kubernetes, Prometheus, and Python.

The current implementation does **not** require a live GCP billing account for the cost-analysis workflow because GCP billing information is represented by mock data.

---

# 1. Deployment Overview

The local environment consists of:

```text
Developer Machine
       |
       +---------------------------+
       |                           |
       v                           v
 Docker Desktop              Python Virtual Environment
       |                           |
       v                           v
 Kubernetes                 Optimization Application
       |
       +-------------------+
       |                   |
       v                   v
 Application          Prometheus
 Workloads            Monitoring
```

The complete setup flow is:

```text
Install Prerequisites
        |
        v
Clone Repository
        |
        v
Create Python Virtual Environment
        |
        v
Install Python Dependencies
        |
        v
Start Docker Desktop
        |
        v
Start Local Kubernetes
        |
        v
Deploy Application Workloads
        |
        v
Deploy Prometheus
        |
        v
Validate Kubernetes
        |
        v
Validate Prometheus
        |
        v
Run Metrics Analyzer
        |
        v
Run Optimization Engine
        |
        v
Generate Recommendations
        |
        v
Test ActionExecutor
```

---

# 2. Prerequisites

The local environment requires the following tools.

| Tool           | Purpose                                |
| -------------- | --------------------------------------- |
| Python 3.12    | Run the optimization application        |
| Docker Desktop | Container runtime and local Kubernetes  |
| Kubernetes     | Run application workloads               |
| kubectl        | Manage Kubernetes resources             |
| Git            | Clone and manage the repository         |
| Prometheus     | Collect workload resource metrics       |

The project was developed and validated using Windows with PowerShell.

---

# 3. Verify Python

Check the installed Python version:

```powershell
python --version
```

The project was developed using Python 3.12.

Expected output should be similar to:

```text
Python 3.12.x
```

---

# 4. Verify Docker

Check Docker:

```powershell
docker --version
```

Docker Desktop should be running before starting the Kubernetes environment.

Verify that the Docker daemon is accessible:

```powershell
docker info
```

If Docker is not running, start Docker Desktop before continuing.

---

# 5. Verify Kubernetes

Check the Kubernetes client:

```powershell
kubectl version --client
```

Then verify cluster connectivity:

```powershell
kubectl cluster-info
```

The project was validated using a local Kubernetes cluster with a node named:

```text
desktop-control-plane
```

---

# 6. Clone the Repository

Clone the project repository:

```powershell
git clone <repository-url>
```

Move into the project directory:

```powershell
cd project1-gcp-cost-optimizer
```

Verify the repository:

```powershell
git status
```

---

# 7. Create Python Virtual Environment

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

After activation, the PowerShell prompt should show:

```text
(.venv)
```

Example:

```text
(.venv) PS C:\...\project1-gcp-cost-optimizer>
```

---

# 8. Install Python Dependencies

Install the project's Python dependencies using the repository dependency file.

If the project contains `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Verify installed packages:

```powershell
pip list
```

The project requires dependencies for areas including:

* Prometheus communication
* Kubernetes API interaction
* Configuration
* Python application execution

---

# 9. Start Docker Desktop

Docker Desktop must be running before creating or accessing the local Kubernetes environment.

Verify:

```powershell
docker info
```

If Docker responds successfully, continue with Kubernetes validation.

---

# 10. Start Local Kubernetes

Ensure Kubernetes is enabled in Docker Desktop.

Then verify:

```powershell
kubectl get nodes
```

Expected state:

```text
NAME                    STATUS   ROLES
desktop-control-plane   Ready    control-plane
```

The exact output may vary depending on the local Kubernetes implementation.

---

# 11. Verify Kubernetes Namespaces

Run:

```powershell
kubectl get namespaces
```

The local environment used during testing contained:

```text
default
kube-node-lease
kube-public
kube-system
local-path-storage
```

The application workloads run in:

```text
default
```

Prometheus runs in:

```text
monitoring
```

The `monitoring` namespace is created as part of the Prometheus deployment process if it does not already exist.

---

# 12. Deploy Application Workloads

The project contains Kubernetes manifests under:

```text
k8s/
```

The application workloads include:

```text
api-service
batch-worker
high-cpu-app
optimized-service
web-app
```

Apply the relevant Kubernetes manifests from the repository.

For example:

```powershell
kubectl apply -f k8s/
```

If the repository contains multiple manifest groups and the manifests are intended to be applied individually, use the specific files instead.

Always inspect the available manifests first:

```powershell
Get-ChildItem k8s
```

---

# 13. Verify Deployments

After applying the Kubernetes manifests:

```powershell
kubectl get deployments
```

The expected application Deployments are:

```text
api-service
batch-worker
high-cpu-app
optimized-service
web-app
```

Wait until the workloads become available.

---

# 14. Verify Pods

Run:

```powershell
kubectl get pods -o wide
```

The expected application Pods should eventually show:

```text
READY   STATUS
1/1     Running
```

Example:

```text
api-service-...          1/1   Running
batch-worker-...         1/1   Running
high-cpu-app-...         1/1   Running
optimized-service-...    1/1   Running
web-app-...              1/1   Running
```

Pod names are generated by Kubernetes and will therefore vary.

---

# 15. Verify Resource Requests

Run:

```powershell
kubectl get pods -o custom-columns="NAME:.metadata.name,CPU_REQUEST:.spec.containers[*].resources.requests.cpu,MEMORY_REQUEST:.spec.containers[*].resources.requests.memory,CPU_LIMIT:.spec.containers[*].resources.limits.cpu,MEMORY_LIMIT:.spec.containers[*].resources.limits.memory"
```

This confirms that the workloads have the resource requests and limits expected by the optimization analyzer.

---

# 16. Deploy Prometheus

Prometheus is deployed into the:

```text
monitoring
```

namespace.

If the namespace does not exist:

```powershell
kubectl create namespace monitoring
```

Apply the Prometheus configuration:

```powershell
kubectl apply -f k8s/prometheus-deployment.yaml
```

If the project contains additional Prometheus configuration files, apply those according to the repository structure.

---

# 17. Verify Prometheus

Check the Prometheus Pod:

```powershell
kubectl get pods -n monitoring
```

Expected state:

```text
prometheus-...   1/1   Running
```

Check the Deployment:

```powershell
kubectl get deployment -n monitoring
```

Expected:

```text
NAME         READY
prometheus   1/1
```

---

# 18. Prometheus Image Issue

During project development, the initial Prometheus deployment used:

```text
prom/prometheus:latest
```

The Pod entered:

```text
ErrImagePull
```

and later:

```text
ImagePullBackOff
```

The Pod events showed an image content retrieval problem.

The deployment was changed to the explicitly versioned image:

```text
prom/prometheus:v3.13.1
```

The versioned image downloaded successfully.

After redeployment, Prometheus reached:

```text
1/1 Running
```

This demonstrates why pinning a known image version can be preferable to relying on the `latest` tag.

---

# 19. Inspect Prometheus Failures

If Prometheus does not start, inspect the Pod:

```powershell
kubectl describe pod <prometheus-pod-name> -n monitoring
```

For example:

```powershell
kubectl describe pod prometheus-756f898594-p7qj2 -n monitoring
```

Check the Events section for:

```text
Failed
ErrImagePull
ImagePullBackOff
```

Also check:

```powershell
kubectl get events -n monitoring
```

---

# 20. Verify Prometheus Service

List services:

```powershell
kubectl get services -n monitoring
```

If Prometheus is exposed through a Kubernetes Service, verify that the Service exists and exposes port:

```text
9090
```

The application uses the Prometheus URL configured in the project configuration.

---

# 21. Port Forward Prometheus

For local browser access, Prometheus can be port-forwarded.

Example:

```powershell
kubectl port-forward -n monitoring deployment/prometheus 9090:9090
```

Prometheus can then be accessed locally through the configured local address and port.

Keep the PowerShell window running while using the port-forward.

---

# 22. Prometheus Availability Check

The Metrics Analyzer checks the Prometheus readiness endpoint.

The application-level test is:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); print(a.connect_to_prometheus())"
```

Successful output:

```text
True
```

This confirms that the Python application can communicate with Prometheus.

---

# 23. Running the Metrics Analyzer

Run the module from the project root:

```powershell
python -m src.metrics_analyzer
```

The module should be executed using the package/module form rather than:

```powershell
python src\metrics_analyzer.py
```

The direct script execution previously produced:

```text
ModuleNotFoundError: No module named 'config'
```

The module execution form correctly preserves the project's import structure.

---

# 24. Verify Prometheus Connectivity

Run:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); print(a.connect_to_prometheus())"
```

Expected:

```text
True
```

If the result is:

```text
False
```

check:

1. Prometheus Pod status
2. Prometheus Service
3. Prometheus URL configuration
4. Port forwarding if required
5. Docker Desktop Kubernetes status

---

# 25. Retrieve Resource Usage

Run:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); import pprint; pprint.pp(a.get_pod_resource_usage())"
```

The result should contain application workloads with CPU and memory usage.

Example structure:

```text
{
    'default/web-app-...': {
        'cpu': ...,
        'memory': ...
    }
}
```

The exact values will vary because the metrics are collected from live workloads.

---

# 26. Retrieve Resource Requests

Run:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); import pprint; pprint.pp(a.get_pod_resource_requests())"
```

The result should include the application workloads and their configured resource requests.

Example:

```text
{
    'default/web-app-...': {
        'cpu': 1.0,
        'memory': 2.0
    }
}
```

---

# 27. Run Utilization Analysis

The utilization pipeline can be tested with:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); pprint.pp(utilization)"
```

This calculates CPU and memory utilization percentages from:

```text
Actual Usage
     /
Resource Request
     ×
100
```

---

# 28. Detect Optimization Opportunities

Run:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); pprint.pp(a.identify_over_provisioned_pods(utilization))"
```

The analyzer identifies workloads that meet the current optimization heuristic.

The local implementation uses:

```text
30% average utilization
```

as the threshold.

---

# 29. Run Waste Analysis

The Optimization Engine can then analyze the identified opportunities.

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); pprint.pp(e.analyze_waste(opportunities))"
```

The output includes:

```text
cpu_waste
memory_waste
```

for each identified workload.

---

# 30. Run Savings Calculation

Savings can be calculated for an individual waste-analysis result:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); waste=e.analyze_waste(opportunities); pprint.pp(e.calculate_savings(waste[0]))"
```

The value returned is an estimated monthly savings amount in INR.

For example, one tested workload returned:

```text
28.45
```

The exact value may change between runs because resource usage is dynamic.

---

# 31. Generate Recommendations

Run:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); pprint.pp(e.generate_recommendations(opportunities))"
```

The output should contain recommendations for workloads identified by the Metrics Analyzer.

Each recommendation includes:

```text
Pod
Current resources
Actual resources
Utilization
Suggested action
Estimated savings
Priority
Priority score
Reason
```

---

# 32. Generate Complete Optimization Report

The full pipeline can be executed using:

```powershell
python -c "from src.cost_fetcher import GCPCostFetcher; from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; c=GCPCostFetcher(); costs=c.fetch_daily_costs(); a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); recommendations=e.generate_recommendations(opportunities); report=e.create_optimization_report(recommendations, costs); print(report['summary']); print(report['text'])"
```

A representative validated result was:

```text
Optimization Opportunities: 5
High Priority: 5
Medium Priority: 0
Low Priority: 0
Estimated Monthly Savings: ₹122.95
```

---

# 33. Run ActionExecutor

Verify the module:

```powershell
python -c "from src.action_executor import ActionExecutor; print('ACTION EXECUTOR OK')"
```

Expected:

```text
ACTION EXECUTOR OK
```

Initialize it:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print(a)"
```

---

# 34. Test Dry-Run Scaling

The ActionExecutor uses dry-run behavior by default.

Test:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print('RESULT:', a.auto_scale_pod('default','web-app',3)); print('AUDIT:', a.action_log)"
```

Expected behavior:

```text
[DRY-RUN] Would execute:
kubectl scale deployment web-app --replicas=3 -n default
```

The method should return:

```text
True
```

No actual scaling operation is performed while dry-run mode is enabled.

---

# 35. Test Protected Namespace

The ActionExecutor should reject modifications to protected namespaces.

Test:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print('RESULT:', a.auto_scale_pod('kube-system','coredns',1)); print('AUDIT:', a.action_log)"
```

Expected:

```text
Refusing to scale protected namespace: kube-system
RESULT: False
```

This confirms that Kubernetes system workloads are protected from automated actions.

---

# 36. Test Invalid Replica Count

Test invalid input:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print(a.auto_scale_pod('default','web-app',0))"
```

Expected:

```text
ValueError:
Replica count must be at least 1
```

This validates input protection.

---

# 37. Test Pod-to-Deployment Resolution

Use a real application Pod:

```powershell
kubectl get pods -l app=web-app
```

Obtain the Pod name and test:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print(a._resolve_deployment_name('default','<pod-name>'))"
```

For the tested environment, a Pod such as:

```text
web-app-79bc9f6b6c-td285
```

resolved to:

```text
web-app
```

This validates:

```text
Pod
 |
 v
ReplicaSet
 |
 v
Deployment
```

resolution.

---

# 38. Test Recommendation Execution

A recommendation can be passed directly to the ActionExecutor.

Example:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); recommendation={'namespace':'default','pod_name':'web-app-79bc9f6b6c-td285','actual_cpu_cores':0.0001,'actual_memory_gb':0.0133,'suggested_action':'Right-size CPU and memory','estimated_monthly_savings_inr':31.95}; print('RESULT:', a.execute_recommendation(recommendation)); print('AUDIT:'); import pprint; pprint.pp(a.action_log)"
```

The validated implementation generated a dry-run resource patch for the `web-app` Deployment.

The proposed action included reduced CPU and memory request/limit values.

No real Kubernetes modification occurred while dry-run mode was enabled.

---

# 39. Generate Weekly Report

The ActionExecutor can also generate a weekly summary.

Example:

```powershell
python -c "from src.action_executor import ActionExecutor; from pathlib import Path; a=ActionExecutor(); recommendations=[{'namespace':'default','pod_name':'web-app','suggested_action':'Right-size CPU and memory','estimated_monthly_savings_inr':31.95},{'namespace':'default','pod_name':'batch-worker','suggested_action':'Consider Spot instance','estimated_monthly_savings_inr':51.10}]; text=a.generate_report_text(recommendations); print(text); print('FILE:', a.send_weekly_report(text, Path('reports')))"
```

The report is written to:

```text
reports\weekly_report.txt
```

The directory is created/used by the reporting functionality as required.

---

# 40. Recommended Startup Order

For normal development, start the environment in this order:

```text
1. Docker Desktop
        |
2. Kubernetes
        |
3. Application workloads
        |
4. Prometheus
        |
5. Verify Pods
        |
6. Verify Prometheus
        |
7. Activate .venv
        |
8. Run Metrics Analyzer
        |
9. Run Optimization Engine
        |
10. Run ActionExecutor tests
```

This ensures that the dependencies required by the Python application are available before analysis begins.

---

# 41. Troubleshooting

## Kubernetes Pod Not Running

Check:

```powershell
kubectl get pods -o wide
```

Then inspect:

```powershell
kubectl describe pod <pod-name>
```

Check events:

```powershell
kubectl get events
```

---

## Prometheus Not Running

Check:

```powershell
kubectl get pods -n monitoring
```

Then:

```powershell
kubectl describe pod <prometheus-pod-name> -n monitoring
```

Look for:

```text
ErrImagePull
ImagePullBackOff
CrashLoopBackOff
```

---

## Prometheus Image Pull Failure

If the Prometheus image cannot be pulled, verify the image configured in:

```text
k8s/prometheus-deployment.yaml
```

The validated local implementation uses:

```text
prom/prometheus:v3.13.1
```

rather than:

```text
prom/prometheus:latest
```

---

## Prometheus Connection Returns False

Run:

```powershell
kubectl get pods -n monitoring
```

Then:

```powershell
kubectl get services -n monitoring
```

Verify the Prometheus URL configured by the application.

If using port forwarding:

```powershell
kubectl port-forward -n monitoring deployment/prometheus 9090:9090
```

---

## `ModuleNotFoundError: config`

If this occurs:

```text
ModuleNotFoundError: No module named 'config'
```

do not execute the module as a standalone script.

Instead, from the project root use:

```powershell
python -m src.metrics_analyzer
```

The project uses package-based imports.

---

## ActionExecutor Import Error

If:

```text
ImportError:
cannot import name 'ActionExecutor'
```

appears, verify the class exists:

```powershell
Select-String -Path src\action_executor.py -Pattern "class "
```

The file should contain:

```text
class ActionExecutor:
```

Then compile it:

```powershell
python -m py_compile src\action_executor.py
```

Finally:

```powershell
python -c "from src.action_executor import ActionExecutor; print('ACTION EXECUTOR OK')"
```

---

# 42. Verify Source Files

The main Python components are:

```text
src/
├── cost_fetcher.py
├── metrics_analyzer.py
├── optimizer_engine.py
└── action_executor.py
```

Verify:

```powershell
Get-ChildItem src
```

---

# 43. Compile Python Modules

Before committing changes, Python source files can be syntax-checked with:

```powershell
python -m py_compile src\cost_fetcher.py
python -m py_compile src\metrics_analyzer.py
python -m py_compile src\optimizer_engine.py
python -m py_compile src\action_executor.py
```

No output generally indicates successful compilation.

---

# 44. Git Validation

After making configuration or code changes:

```powershell
git status
```

Review changes:

```powershell
git diff
```

For a specific file:

```powershell
git diff -- src\action_executor.py
```

Before committing, verify that only intended files were modified.

---

# 45. Stopping the Environment

The local environment can be stopped when development is complete.

Application workloads can be removed with:

```powershell
kubectl delete -f k8s/
```

Use this only if the manifests are intended to be deleted together.

Alternatively, delete individual resources:

```powershell
kubectl delete deployment <deployment-name>
```

Prometheus can be removed separately if required:

```powershell
kubectl delete -f k8s/prometheus-deployment.yaml
```

If the project uses additional Prometheus resources, delete those according to the repository structure.

---

# 46. Important Safety Note

The ActionExecutor is configured for dry-run behavior in the local development environment.

Do not change the execution mode to real Kubernetes modification without first validating:

* Resource recommendations
* Historical utilization
* Workload behavior
* Safety margins
* Namespace policies
* Deployment targeting
* Container targeting
* Rollback procedures
* Monitoring
* Application SLOs

A resource optimization recommendation is not automatically a safe production change.

---

# 47. Production Deployment Considerations

The current deployment is intentionally local.

A production implementation would require additional infrastructure.

A potential production architecture would be:

```text
                    GCP
                     |
        +------------+-------------+
        |                          |
        v                          v
 GCP Billing Export            GKE Cluster
        |                          |
        v                          v
    BigQuery                  Prometheus
        |                          |
        +------------+-------------+
                     |
                     v
             Optimization Service
                     |
                     v
             Recommendation Layer
                     |
                     v
              Approval / Policy
                     |
                     v
              Action Executor
                     |
                     v
              GKE Workloads
```

---

# 48. Production Prerequisites

A future GCP deployment would require:

* GCP project
* GKE cluster
* Appropriate IAM permissions
* GCP Billing Export
* BigQuery dataset
* Prometheus monitoring
* Secret/configuration management
* Centralized logging
* Audit storage
* Production deployment strategy
* CI/CD pipeline

The current repository does not claim that these production components are implemented.

---

# 49. GCP Billing Integration

The current implementation uses:

```text
Mock Cost Data
```

for local development.

A future implementation can replace this with:

```text
GCP Billing Export
        |
        v
BigQuery
        |
        v
Cost Fetcher
```

The Cost Fetcher abstraction is intended to keep this integration separate from the optimization engine.

---

# 50. Production Action Execution

The local environment uses:

```text
Dry Run = Enabled
```

A production system should introduce additional controls before enabling real actions.

A safer architecture would be:

```text
Recommendation
      |
      v
Policy Validation
      |
      v
Approval
      |
      v
ActionExecutor
      |
      v
Kubernetes
      |
      v
Audit Log
```

This prevents an optimization recommendation from directly becoming an infrastructure mutation.

---

# 51. Deployment Validation Checklist

Before considering the local environment ready, verify:

```text
[ ] Docker Desktop running
[ ] Kubernetes cluster running
[ ] Kubernetes node Ready
[ ] Application Deployments available
[ ] Application Pods Running
[ ] Resource requests configured
[ ] Monitoring namespace available
[ ] Prometheus Pod Running
[ ] Prometheus Deployment Available
[ ] Prometheus connectivity returns True
[ ] Resource usage retrieval works
[ ] Resource request retrieval works
[ ] Utilization calculation works
[ ] Over-provisioning detection works
[ ] Waste analysis works
[ ] Savings calculation works
[ ] Recommendation generation works
[ ] Optimization report works
[ ] ActionExecutor imports successfully
[ ] Dry-run scaling works
[ ] Protected namespace is rejected
[ ] Invalid replica count is rejected
[ ] Pod-to-Deployment resolution works
[ ] Audit logging works
[ ] Weekly report generation works
```

---

# 52. Quick Start

For an already configured development machine, the shortened workflow is:

```powershell
# Activate environment
.venv\Scripts\Activate.ps1

# Verify Kubernetes
kubectl get nodes

# Verify application workloads
kubectl get pods -o wide

# Verify Prometheus
kubectl get pods -n monitoring

# Test Prometheus connectivity
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); print(a.connect_to_prometheus())"

# Test resource usage
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); import pprint; pprint.pp(a.get_pod_resource_usage())"

# Test resource requests
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); import pprint; pprint.pp(a.get_pod_resource_requests())"

# Test ActionExecutor
python -c "from src.action_executor import ActionExecutor; print('ACTION EXECUTOR OK')"
```

Then execute the full optimization pipeline.

---

# 53. Full Validation Workflow

The complete local validation workflow is:

```text
Docker Desktop
      |
      v
Kubernetes
      |
      v
Application Workloads
      |
      v
Prometheus
      |
      v
Prometheus Connectivity
      |
      v
Resource Usage
      |
      v
Resource Requests
      |
      v
Utilization
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
Optimization Report
      |
      v
ActionExecutor
      |
      v
Dry-Run Kubernetes Action
      |
      v
Audit / Weekly Report
```

---

# 54. Local Deployment Status

The local environment was successfully validated with:

```text
Docker
    PASS

Kubernetes
    PASS

Application Workloads
    PASS

Prometheus
    PASS

Python Application
    PASS

Metrics Analysis
    PASS

Optimization Engine
    PASS

ActionExecutor
    PASS

Dry-Run Execution
    PASS

Safety Controls
    PASS

Reporting
    PASS
```

The local implementation is therefore suitable for demonstration and portfolio purposes.

---

# 55. Current Deployment Boundary

It is important to distinguish between what has been implemented and what remains future work.

## Implemented and Validated

* Local Kubernetes
* Application workloads
* Prometheus
* Prometheus connectivity
* Resource usage collection
* Kubernetes resource request collection
* Optimization analysis
* Savings estimation
* Recommendation generation
* Optimization reporting
* Dry-run Kubernetes actions
* Namespace protection
* Audit logging
* Weekly reporting

## Future

* Real GCP Billing Export
* BigQuery cost integration
* GKE deployment
* Production authentication
* Production IAM
* Persistent audit storage
* Historical metrics analysis
* Automated scheduling
* Production approval workflows
* Web dashboard
* Production-grade CI/CD

---

# 56. Summary

The project can be reproduced locally without requiring paid GCP infrastructure.

The deployment architecture uses:

```text
Docker Desktop
      |
      v
Local Kubernetes
      |
      +----------------+
      |                |
      v                v
Application        Prometheus
Workloads          Monitoring
      |                |
      +-------+--------+
              |
              v
       Python Application
              |
       +------+------+
       |             |
       v             v
 Metrics         Optimization
 Analyzer          Engine
       |             |
       +------+------+
              |
              v
        ActionExecutor
              |
              v
         Dry-Run Actions
```

The local environment provides a complete demonstration of the project's core workflow while keeping cloud billing and infrastructure modification safely isolated.

The architecture can later be extended to GCP/GKE with real billing data, historical utilization analysis, production IAM, approval workflows, and controlled infrastructure automation.
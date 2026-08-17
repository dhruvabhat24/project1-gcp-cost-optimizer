# Testing and Validation

## GCP Cost Optimizer for Kubernetes

This document describes the testing and validation performed on the GCP Cost Optimizer for Kubernetes.

The objective of testing was to verify the complete optimization pipeline from Kubernetes and Prometheus data collection through recommendation generation, reporting, and safe Kubernetes action execution.

The project was tested locally using:

- Windows
- Docker Desktop
- Local Kubernetes
- Prometheus
- Python virtual environment
- Kubernetes workloads
- Mock GCP cost data

The tests were performed incrementally so that individual components could be validated before testing the complete workflow.

---

# 1. Testing Strategy

The project was validated using a combination of:

- Environment validation
- Kubernetes validation
- Prometheus validation
- Python module validation
- Component-level testing
- Integration testing
- End-to-end pipeline testing
- Safety testing
- Negative testing
- Dry-run execution testing
- Audit logging validation
- Report generation validation

The overall testing flow was:

```text
Environment
    |
    v
Kubernetes
    |
    v
Prometheus
    |
    v
Metrics Analyzer
    |
    v
Optimization Engine
    |
    v
ActionExecutor
    |
    v
Reports / Audit
```

---

# 2. Test Environment

The project was executed inside the Python virtual environment:

```text
(.venv)
```

The working project directory was:

```text
project1-gcp-cost-optimizer
```

The local Kubernetes cluster was running successfully.

The Kubernetes node used during testing was:

```text
desktop-control-plane
```

---

# 3. Kubernetes Cluster Validation

The first validation step was confirming that the Kubernetes workloads were running.

Command:

```powershell
kubectl get pods -o wide
```

The application workloads were:

```text
api-service
batch-worker
high-cpu-app
optimized-service
web-app
```

All five application Pods reached:

```text
1/1 Running
```

The resulting state confirmed that the test workloads were available for metrics collection.

---

# 4. Kubernetes Resource Request Validation

The resource requests and limits configured on the workloads were inspected using:

```powershell
kubectl get pods -o custom-columns="NAME:.metadata.name,CPU_REQUEST:.spec.containers[*].resources.requests.cpu,MEMORY_REQUEST:.spec.containers[*].resources.requests.memory,CPU_LIMIT:.spec.containers[*].resources.limits.cpu,MEMORY_LIMIT:.spec.containers[*].resources.limits.memory"
```

The validated application resource requests were:

| Workload          | CPU Request | Memory Request | CPU Limit | Memory Limit |
| ------------------ | -----------: | ---------------: | ----------: | -------------: |
| api-service         |            1 |              1Gi |       1500m |            2Gi |
| batch-worker        |            1 |              2Gi |           2 |            2Gi |
| high-cpu-app        |         500m |            500Mi |        750m |          750Mi |
| optimized-service   |          50m |             50Mi |        100m |          100Mi |
| web-app             |            1 |              2Gi |       1500m |            2Gi |

This confirmed that the test workloads had intentionally different resource configurations.

That variation was useful for demonstrating the optimizer's ability to identify different levels of potential resource waste.

---

# 5. Kubernetes Namespace Validation

The available namespaces were checked with:

```powershell
kubectl get namespaces
```

The local cluster contained:

```text
default
kube-node-lease
kube-public
kube-system
local-path-storage
```

The application workloads were running in:

```text
default
```

Prometheus was deployed into:

```text
monitoring
```

Kubernetes system components remained in:

```text
kube-system
```

This namespace separation was later used to validate ActionExecutor safety controls.

---

# 6. Prometheus Deployment Validation

Prometheus was deployed in the `monitoring` namespace.

The initial deployment experienced an image-pull problem.

The Pod initially entered:

```text
ErrImagePull
```

and subsequently:

```text
ImagePullBackOff
```

---

# 7. Prometheus Image Pull Failure

The Pod was inspected using:

```powershell
kubectl describe pod prometheus-766999f885-72cq7 -n monitoring
```

The relevant error indicated that:

```text
prom/prometheus:latest
```

could not be pulled successfully.

The error reported a missing image content descriptor from the registry.

This was treated as an environment/image-resolution issue rather than an application logic failure.

---

# 8. Prometheus Image Resolution

A versioned Prometheus image was pulled successfully:

```text
prom/prometheus:v3.13.1
```

The image download completed successfully.

The output included:

```text
Status: Downloaded newer image for prom/prometheus:v3.13.1
```

After updating the deployment to use the versioned image, the Pod became healthy.

---

# 9. Prometheus Final Validation

The Prometheus Pod was checked with:

```powershell
kubectl get pods -n monitoring
```

The final result was:

```text
prometheus-756f898594-p7qj2   1/1   Running
```

The Deployment was also verified:

```powershell
kubectl get deployment -n monitoring
```

Result:

```text
NAME         READY   UP-TO-DATE   AVAILABLE
prometheus   1/1     1            1
```

This confirmed that Prometheus was successfully running in Kubernetes.

---

# 10. Metrics Analyzer Import Validation

The Metrics Analyzer initially produced an import issue when executed directly.

Command:

```powershell
python src\metrics_analyzer.py
```

Result:

```text
ModuleNotFoundError: No module named 'config'
```

The issue was caused by running the module as a standalone script rather than as part of the Python package structure.

The module was subsequently executed using:

```powershell
python -m src.metrics_analyzer
```

This executed successfully.

This validated the package/module execution model used by the project.

---

# 11. Prometheus Connectivity Test

Prometheus connectivity was explicitly tested with:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); print(a.connect_to_prometheus())"
```

Result:

```text
True
```

This confirmed that:

```text
Python
   |
   v
Metrics Analyzer
   |
   v
Prometheus
```

connectivity was working.

---

# 12. Resource Usage Retrieval Test

The next test validated that actual resource utilization could be retrieved from Prometheus.

Command:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); import pprint; pprint.pp(a.get_pod_resource_usage())"
```

The analyzer returned resource usage for the application workloads.

Example results included:

```text
default/api-service
CPU ≈ 0.000085
Memory ≈ 0.0132 GB

default/batch-worker
CPU ≈ 0.0028
Memory ≈ 0.0064 GB

default/high-cpu-app
CPU ≈ 0.1492
Memory ≈ 0.0027 GB

default/optimized-service
CPU ≈ 0.0001
Memory ≈ 0.0132 GB

default/web-app
CPU ≈ 0.00007
Memory ≈ 0.0133 GB
```

The exact values changed between executions because Prometheus was collecting live workload metrics.

The important validation result was that workload-level CPU and memory usage was successfully retrieved.

---

# 13. Resource Request Retrieval Test

The Kubernetes resource request retrieval method was tested independently.

Command:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); import pprint; pprint.pp(a.get_pod_resource_requests())"
```

The analyzer returned:

```text
default/api-service
CPU: 1.0
Memory: 1.0 GB

default/batch-worker
CPU: 1.0
Memory: 2.0 GB

default/high-cpu-app
CPU: 0.5
Memory: ~0.4883 GB

default/optimized-service
CPU: 0.05
Memory: ~0.0488 GB

default/web-app
CPU: 1.0
Memory: 2.0 GB
```

This confirmed that the application could retrieve Kubernetes resource requests and normalize them into the expected structure.

---

# 14. Utilization Calculation Test

The utilization calculation was tested using both usage and request data.

The pipeline was:

```text
Usage
  +
Requests
  |
  v
calculate_utilization_percent()
```

The resulting values demonstrated that CPU and memory utilization percentages were being calculated correctly.

Example:

```text
web-app

CPU Request:
1.0 core

CPU Usage:
~0.0001 core

CPU Utilization:
~0.01%
```

and:

```text
Memory Request:
2.0 GB

Memory Usage:
~0.0133 GB

Memory Utilization:
~0.67%
```

---

# 15. Over-Provisioning Detection Test

The over-provisioning detector was tested using:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); pprint.pp(a.identify_over_provisioned_pods(utilization))"
```

The test identified all five application workloads as optimization opportunities during the observed test period.

The returned reason was:

```text
Resource utilization below 30%
```

The result included:

```text
api-service
batch-worker
high-cpu-app
optimized-service
web-app
```

This validated the 30% heuristic used by the current implementation.

---

# 16. Waste Analysis Test

The Metrics Analyzer output was passed to the Optimization Engine.

Command:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); pprint.pp(e.analyze_waste(opportunities))"
```

The engine successfully added:

```text
cpu_waste
memory_waste
```

to each opportunity.

Example:

```text
api-service

CPU Waste:
~0.9999 cores

Memory Waste:
~0.9868 GB
```

Another example:

```text
web-app

CPU Waste:
~0.9999 cores

Memory Waste:
~1.9867 GB
```

This confirmed that the waste-analysis stage was functioning correctly.

---

# 17. Savings Calculation Bug and Fix

During testing, the savings calculation initially produced an error.

The test command was:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); waste=e.analyze_waste(opportunities); pprint.pp(e.calculate_savings(waste))"
```

The error was:

```text
AttributeError: 'list' object has no attribute 'get'
```

The issue was that:

```text
calculate_savings()
```

expects a single Pod analysis dictionary, while:

```text
analyze_waste()
```

returns a list.

The corrected test used an individual item:

```text
e.calculate_savings(waste[0])
```

This successfully returned:

```text
28.45
```

The issue demonstrated the importance of validating both the component implementation and the expected data contract between methods.

---

# 18. Recommendation Engine Test

The recommendation engine was tested after the waste-analysis stage.

Command:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); waste=e.analyze_waste(opportunities); pprint.pp(e.generate_recommendations(opportunities))"
```

The engine successfully generated recommendations for all five application workloads.

The recommendations included:

```text
suggested_action
estimated_monthly_savings_inr
implementation_priority
priority_score
```

All five workloads were classified as High priority during the tested run.

---

# 19. Recommendation Results

A representative test result was:

| Workload          | Estimated Monthly Savings | Priority |
| ------------------ | --------------------------: | -------- |
| batch-worker        |                      ₹51.10 | High     |
| web-app             |                      ₹31.95 | High     |
| api-service         |                      ₹28.45 | High     |
| optimized-service   |                       ₹1.37 | High     |
| high-cpu-app        |                        ~₹10 | High     |

The exact values may vary slightly between runs because Prometheus utilization is dynamic.

---

# 20. Optimization Report Test

The complete report generation pipeline was tested using:

```powershell
python -c "from src.cost_fetcher import GCPCostFetcher; from src.metrics_analyzer import PrometheusMetricsAnalyzer; from src.optimizer_engine import CostOptimizationEngine; import pprint; c=GCPCostFetcher(); costs=c.fetch_daily_costs(); a=PrometheusMetricsAnalyzer(); a.connect_to_prometheus(); usage=a.get_pod_resource_usage(); requests=a.get_pod_resource_requests(); utilization=a.calculate_utilization_percent(usage, requests); opportunities=a.identify_over_provisioned_pods(utilization); e=CostOptimizationEngine(); recommendations=e.generate_recommendations(opportunities); report=e.create_optimization_report(recommendations, costs); print(report['summary']); print(); print(report['text'])"
```

The test produced:

```text
Optimization Opportunities: 5
High Priority: 5
Medium Priority: 0
Low Priority: 0
Estimated Monthly Savings: ₹122.95
```

The report also included mock GCP cost information.

---

# 21. Final Optimization Report Result

The validated report contained:

```text
GCP Project:
demo-project

Cost Source:
mock

7-Day GCP Cost:
₹1,030.80

Estimated Monthly GCP Cost:
₹4,417.71

Optimization Opportunities:
5

High Priority:
5

Medium Priority:
0

Low Priority:
0

Estimated Monthly Savings:
₹122.95
```

The report also contained detailed recommendations for each workload.

---

# 22. ActionExecutor Import Test

The ActionExecutor was tested independently.

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; print('ACTION EXECUTOR IMPORT OK')"
```

Result:

```text
ACTION EXECUTOR IMPORT OK
```

This confirmed that the module could be imported successfully.

---

# 23. ActionExecutor Initialization Test

The class was instantiated using:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print(a)"
```

The result successfully returned an `ActionExecutor` object.

This confirmed that initialization completed without errors.

---

# 24. Dry-Run Scaling Test

The ActionExecutor was tested using a valid application workload.

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print('RESULT:', a.auto_scale_pod('default','web-app',3)); print('AUDIT:', a.action_log)"
```

The output was:

```text
[DRY-RUN] Would execute:
kubectl scale deployment web-app --replicas=3 -n default
```

Result:

```text
RESULT: True
```

An audit record was also generated:

```text
{
    "namespace": "default",
    "resource": "web-app",
    "action": "scale",
    "new_value": 3,
    "dry_run": true
}
```

This validated the dry-run execution path.

---

# 25. Protected Namespace Test

The ActionExecutor was tested against the protected `kube-system` namespace.

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print('RESULT:', a.auto_scale_pod('kube-system','coredns',1)); print('AUDIT:', a.action_log)"
```

Result:

```text
Refusing to scale protected namespace: kube-system
RESULT: False
AUDIT: []
```

This successfully demonstrated that protected namespace operations are rejected.

No audit action was generated because the operation was refused before execution.

---

# 26. Invalid Replica Count Test

The ActionExecutor was tested with an invalid replica count:

```text
0
```

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print(a.auto_scale_pod('default','web-app',0))"
```

The executor raised:

```text
ValueError:
Replica count must be at least 1
```

This validated input validation for scaling operations.

---

# 27. Protected Namespace Resource Update Test

Resource updates against protected namespaces were also tested.

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print('RESULT:', a.update_resource_limits('kube-system','coredns','100m','128Mi')); print('AUDIT:', a.action_log)"
```

Result:

```text
Refusing to modify protected namespace: kube-system
RESULT: False
AUDIT: []
```

This confirmed that namespace protection applies to resource modifications as well as scaling.

---

# 28. Audit Logging Test

The audit logging method was tested directly.

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; import pprint; a=ActionExecutor(); a.log_action('default','web-app',{'replicas':5},{'replicas':3},'scale'); pprint.pp(a.action_log)"
```

The resulting audit entry included:

```text
timestamp
namespace
resource
action
old_value
new_value
dry_run
```

Example:

```text
{
    'namespace': 'default',
    'resource': 'web-app',
    'action': 'scale',
    'old_value': {'replicas': 5},
    'new_value': {'replicas': 3},
    'dry_run': True
}
```

This validated the audit logging mechanism.

---

# 29. Pod-to-Deployment Resolution Test

Optimization recommendations contain Pod names, while scaling and resource patching operate on Deployments.

The ActionExecutor was therefore tested using a real Pod name:

```text
web-app-79bc9f6b6c-td285
```

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; a=ActionExecutor(); print('DEPLOYMENT:', a._resolve_deployment_name('default','web-app-79bc9f6b6c-td285'))"
```

Result:

```text
DEPLOYMENT: web-app
```

This confirmed the Pod → ReplicaSet → Deployment resolution logic.

---

# 30. Kubernetes Label Validation

The application workload Pod was also located using its Kubernetes label.

Command:

```powershell
kubectl get pods -l app=web-app
```

Result:

```text
web-app-79bc9f6b6c-td285
```

The Pod was confirmed to be:

```text
1/1 Running
```

This provided additional validation that the ActionExecutor was operating against a real local workload.

---

# 31. Deployment Container Validation

The container names of the application Deployments were checked directly.

Commands:

```powershell
kubectl get deployment web-app -o jsonpath="{.spec.template.spec.containers[*].name}"
```

and:

```powershell
kubectl get deployment api-service -o jsonpath="{.spec.template.spec.containers[*].name}"
kubectl get deployment optimized-service -o jsonpath="{.spec.template.spec.containers[*].name}"
kubectl get deployment high-cpu-app -o jsonpath="{.spec.template.spec.containers[*].name}"
kubectl get deployment batch-worker -o jsonpath="{.spec.template.spec.containers[*].name}"
```

The validated container names corresponded to their application workloads:

```text
web-app
api-service
optimized-service
high-cpu-app
batch-worker
```

This confirmed that the ActionExecutor could target the expected application containers.

---

# 32. Recommendation Execution Test

A complete recommendation was passed to the ActionExecutor.

The test recommendation represented the `web-app` workload:

```text
namespace:
default

pod_name:
web-app-79bc9f6b6c-td285

actual_cpu_cores:
0.0001

actual_memory_gb:
0.0133

suggested_action:
Right-size CPU and memory

estimated_monthly_savings_inr:
31.95
```

The command generated a dry-run Kubernetes patch:

```text
[DRY-RUN] Would execute:

kubectl patch deployment web-app -n default --type=strategic ...
```

The proposed resource values were:

```text
CPU:
0.010

Memory:
0.020Gi
```

The result was:

```text
RESULT: True
```

An audit record was also generated.

This validated the integration between the recommendation structure and the ActionExecutor.

---

# 33. Weekly Report Test

The weekly reporting functionality was tested using sample recommendations.

Command:

```powershell
python -c "from src.action_executor import ActionExecutor; from pathlib import Path; a=ActionExecutor(); recommendations=[{'namespace':'default','pod_name':'web-app','suggested_action':'Right-size CPU and memory','estimated_monthly_savings_inr':31.95},{'namespace':'default','pod_name':'batch-worker','suggested_action':'Consider Spot instance','estimated_monthly_savings_inr':51.10}]; text=a.generate_report_text(recommendations); print(text); print('FILE:', a.send_weekly_report(text, Path('reports')))"
```

The generated report contained:

```text
Kubernetes Cost Optimizer - Weekly Summary
==================================================
Recommendations: 2
Estimated monthly savings: ₹83.05

- default/web-app: Right-size CPU and memory | ₹31.95/month
- default/batch-worker: Consider Spot instance | ₹51.10/month
```

The report was successfully written to:

```text
reports\weekly_report.txt
```

This validated the weekly reporting functionality.

---

# 34. Complete Integration Test

The complete optimization pipeline was successfully executed using:

```text
Cost Fetcher
     |
     v
Metrics Analyzer
     |
     +--> Prometheus Usage
     |
     +--> Kubernetes Requests
     |
     v
Utilization Analysis
     |
     v
Over-Provisioning Detection
     |
     v
Optimization Engine
     |
     +--> Waste Analysis
     |
     +--> Savings Calculation
     |
     +--> Recommendations
     |
     v
Optimization Report
     |
     v
ActionExecutor
     |
     v
Dry-Run Action
     |
     v
Audit Log
```

The successful final report demonstrated:

```text
5 optimization opportunities
5 high-priority recommendations
₹122.95 estimated monthly savings
```

---

# 35. Test Coverage Summary

| Area                 | Test                          | Result |
| --------------------- | ------------------------------ | ------ |
| Kubernetes            | Application Pods running       | PASS   |
| Kubernetes            | Resource requests              | PASS   |
| Kubernetes            | Namespace validation           | PASS   |
| Prometheus            | Deployment                     | PASS   |
| Prometheus            | Connectivity                   | PASS   |
| Metrics Analyzer      | Resource usage retrieval       | PASS   |
| Metrics Analyzer      | Resource request retrieval     | PASS   |
| Metrics Analyzer      | Utilization calculation        | PASS   |
| Metrics Analyzer      | Over-provisioning detection    | PASS   |
| Optimization Engine   | Waste analysis                 | PASS   |
| Optimization Engine   | Savings calculation            | PASS   |
| Optimization Engine   | Recommendation generation      | PASS   |
| Optimization Engine   | Priority scoring                | PASS   |
| Reporting             | Optimization report            | PASS   |
| ActionExecutor        | Import                          | PASS   |
| ActionExecutor        | Initialization                  | PASS   |
| ActionExecutor        | Deployment resolution           | PASS   |
| ActionExecutor        | Dry-run scaling                 | PASS   |
| ActionExecutor        | Dry-run resource patch          | PASS   |
| ActionExecutor        | Protected namespace             | PASS   |
| ActionExecutor        | Invalid replica validation      | PASS   |
| ActionExecutor        | Audit logging                   | PASS   |
| Reporting             | Weekly report                   | PASS   |

---

# 36. Issues Encountered During Testing

Testing was not completely linear.

Several issues were encountered and resolved during development.

---

## 36.1 Prometheus Image Pull Failure

Initial Prometheus deployment used:

```text
prom/prometheus:latest
```

The Pod entered:

```text
ErrImagePull
```

and then:

```text
ImagePullBackOff
```

The image was replaced with the explicitly versioned:

```text
prom/prometheus:v3.13.1
```

After the change, Prometheus started successfully.

---

## 36.2 Python Module Import Error

Running:

```powershell
python src\metrics_analyzer.py
```

produced:

```text
ModuleNotFoundError: No module named 'config'
```

The module was correctly executed using:

```powershell
python -m src.metrics_analyzer
```

This resolved the package import context.

---

## 36.3 Savings Calculation Input Error

An early test passed the complete waste-analysis list into:

```text
calculate_savings()
```

which expects a single dictionary.

The resulting error was:

```text
AttributeError: 'list' object has no attribute 'get'
```

The test was corrected to pass an individual analysis item:

```text
waste[0]
```

The method then successfully returned a savings value.

---

## 36.4 ActionExecutor Class Replacement Error

During ActionExecutor development, the wrong class content temporarily existed in:

```text
src/action_executor.py
```

The module contained:

```text
class PrometheusMetricsAnalyzer
```

instead of:

```text
class ActionExecutor
```

As a result:

```text
ImportError:
cannot import name 'ActionExecutor'
```

was observed.

The file was corrected and subsequently validated with:

```powershell
python -m py_compile src\action_executor.py
```

followed by:

```powershell
python -c "from src.action_executor import ActionExecutor; print('ACTION EXECUTOR OK')"
```

The final result was:

```text
ACTION EXECUTOR OK
```

---

# 37. Compilation Validation

The ActionExecutor source was explicitly compiled using:

```powershell
python -m py_compile src\action_executor.py
```

No compilation error was returned.

This confirmed that the Python source was syntactically valid.

The same principle can be applied to the other project modules before final release.

---

# 38. Safety Test Results

The ActionExecutor safety behavior was validated using both valid and invalid operations.

### Valid operation

```text
default/web-app
replicas = 3
```

Result:

```text
Dry-run successful
```

### Protected namespace

```text
kube-system/coredns
```

Result:

```text
Operation refused
```

### Invalid replica count

```text
replicas = 0
```

Result:

```text
ValueError
```

These tests demonstrate that the execution layer is not simply passing every request directly to Kubernetes.

---

# 39. Test Philosophy

The testing process followed a progressive validation approach.

Instead of testing the entire application immediately, individual layers were validated first.

```text
Layer 1
Environment
    |
    v
Layer 2
Kubernetes
    |
    v
Layer 3
Prometheus
    |
    v
Layer 4
Metrics Analyzer
    |
    v
Layer 5
Optimization Engine
    |
    v
Layer 6
ActionExecutor
    |
    v
Layer 7
End-to-End Pipeline
```

This approach made it easier to isolate failures.

---

# 40. Reproducibility

The core tests can be repeated from the project root.

Example environment validation:

```powershell
kubectl get pods -o wide
```

Prometheus validation:

```powershell
kubectl get pods -n monitoring
```

Python module validation:

```powershell
python -m src.metrics_analyzer
```

Prometheus connectivity:

```powershell
python -c "from src.metrics_analyzer import PrometheusMetricsAnalyzer; a=PrometheusMetricsAnalyzer(); print(a.connect_to_prometheus())"
```

ActionExecutor validation:

```powershell
python -c "from src.action_executor import ActionExecutor; print('ACTION EXECUTOR OK')"
```

The exact Prometheus usage values and calculated savings may vary between runs because workload utilization is dynamic.

---

# 41. What the Tests Prove

The tests demonstrate that the local implementation can successfully:

```text
1. Run Kubernetes workloads
        |
2. Run Prometheus
        |
3. Connect Python to Prometheus
        |
4. Retrieve workload utilization
        |
5. Retrieve Kubernetes resource requests
        |
6. Calculate utilization
        |
7. Identify potential over-provisioning
        |
8. Calculate resource waste
        |
9. Estimate potential savings
        |
10. Generate prioritized recommendations
        |
11. Generate optimization reports
        |
12. Resolve Pods to Deployments
        |
13. Generate safe dry-run actions
        |
14. Reject protected namespace operations
        |
15. Reject invalid replica counts
        |
16. Record audit information
        |
17. Generate weekly reports
```

---

# 42. Testing Limitations

The current validation has several limitations.

## Local Environment

Testing was performed on a local Kubernetes cluster rather than a production GKE environment.

## Mock Billing

GCP billing data is represented by mock data.

## Dry-Run Execution

Kubernetes modifications were simulated rather than applied.

## Dynamic Metrics

Prometheus utilization values can change between test executions.

## Limited Workload Diversity

The test cluster contains a small number of intentionally configured workloads.

Therefore, the results demonstrate functional correctness of the local system but should not be interpreted as production-scale performance validation.

---

# 43. Future Testing Improvements

A production implementation could introduce:

* Automated unit tests
* Pytest test suites
* Integration tests
* Kubernetes test fixtures
* Prometheus test data
* Mock GCP Billing APIs
* CI/CD pipeline testing
* Static analysis
* Type checking
* Security scanning
* Container image scanning
* Performance testing
* Load testing
* Multi-cluster testing
* Real GCP billing validation
* Real Kubernetes mutation tests in a disposable environment

A future CI pipeline could look like:

```text
Git Push
   |
   v
Lint
   |
   v
Type Check
   |
   v
Unit Tests
   |
   v
Integration Tests
   |
   v
Security Scan
   |
   v
Build
   |
   v
Deploy Test Environment
   |
   v
End-to-End Tests
   |
   v
Release
```

---

# 44. Final Validation Status

At the completion of local testing, the major components were validated successfully.

```text
Kubernetes
    PASS

Prometheus
    PASS

Metrics Analyzer
    PASS

Optimization Engine
    PASS

Recommendation Engine
    PASS

Optimization Report
    PASS

ActionExecutor
    PASS

Safety Controls
    PASS

Audit Logging
    PASS

Weekly Reporting
    PASS

End-to-End Pipeline
    PASS
```

The local implementation therefore provides a functioning demonstration of the complete optimization workflow.

---

# 45. Final Test Result

The final end-to-end optimization test produced:

```text
Optimization Opportunities: 5
High Priority: 5
Medium Priority: 0
Low Priority: 0
Estimated Monthly Savings: ₹122.95
```

The result confirms that the project successfully connects:

```text
Kubernetes
     +
Prometheus
     +
Cost Data
     |
     v
Optimization Analysis
     |
     v
Recommendations
     |
     v
Safe Kubernetes Actions
     |
     v
Audit / Reporting
```

The project is therefore functionally validated in the local development environment.

The remaining distinction is that the current environment uses mock billing data and dry-run infrastructure actions, so production deployment would require additional validation against real GCP billing data and a controlled GKE environment.
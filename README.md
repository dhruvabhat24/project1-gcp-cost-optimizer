# Kubernetes Cost Optimizer

A Python-based Kubernetes FinOps automation system that analyzes Kubernetes
resource utilization against requested CPU and memory resources, identifies
over-provisioned workloads, estimates infrastructure savings, and produces
weekly optimization reports.

The project is designed as a DevOps portfolio project demonstrating
Kubernetes, Prometheus, Python automation, GCP cost analysis, GitHub Actions,
resource right-sizing, and safe infrastructure automation.

---

## Architecture

```text
                    +-----------------------+
                    |    GitHub Actions     |
                    | Daily / Push Trigger  |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Kubernetes Cost       |
                    | Optimizer             |
                    |       Python          |
                    +-----------+-----------+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
      +------------------+              +------------------+
      |   Prometheus     |              |    GCP Billing   |
      | CPU / Memory     |              | Cost Data        |
      +------------------+              +------------------+
               |                                 |
               +----------------+----------------+
                                |
                                v
                    +-----------------------+
                    | Optimization Engine   |
                    |                       |
                    | Right-size            |
                    | Scale                  |
                    | Spot recommendations  |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Weekly Report         |
                    | JSON + TXT             |
                    +-----------------------+
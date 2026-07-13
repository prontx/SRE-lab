# Cloud-Native lab

Leveraging my 5 years of OpenStack/RHOSP
production support engineering experience to cloud-native SRE practice. Everything here is
built from scratch, provisioned as code, and destroyed after each session.

## Contents

### `terraform/aws/` — Infrastructure as Code on AWS ✅
- VPC, subnet, routing (IGW, route tables) assembled explicitly — the AWS
  equivalent of what Neutron's `router-gateway-set` does implicitly
- EC2 provisioning with SSH keypair management and AMI lookup via data sources
  (no hardcoded, region-rotting AMI IDs)
- Security groups locked to /32 source
- k3s single-node Kubernetes bootstrapped at boot via cloud-init `user_data`
- State hygiene: tfstate excluded from VCS, provider versions pinned via lock file

### `k8s/` — Kubernetes ops. In progress
- Remote kubectl access (TLS SAN problem — see below)
- Helm-deployed observability stack: Prometheus, Grafana, Loki
- GitOps with Flux/ArgoCD
- CI/CD via GitHub Actions

## Incidents & lessons so far

Real problems hit and diagnosed along the way:

- **"TLS handshake timeout" on localhost kubectl** -> not a TLS problem.
  Diagnosed via `free -m` / `dmesg` / `top` as memory starvation: k3s control
  plane on a 1GB t3.micro left 29MB available. Symptoms lie about their layer.
  Fixed by right-sizing to t3.small. 
- **Drift detection in practice**: manually tagged a VPC in the console,
  watched `terraform plan` propose reverting it.
- **State is the boundary of Terraform's world**: tagged the wrong (default)
  VPC, Terraform didn't blink. Resources outside state are invisible.

## Background

The mental model transfer from OpenStack is the point of this repo:

| OpenStack        | AWS / cloud-native          |
|------------------|-----------------------------|
| Neutron network  | VPC                         |
| router-gateway   | Internet Gateway + routes   |
| Floating IP      | Elastic IP / auto-assign    |
| Heat             | Terraform / CloudFormation  |
| Glance image     | AMI (per-region!)           |
| Keystone 403     | IAM deny-by-default         |

## TODO
- [ ] Least-privilege IAM policy for the terraform user (lab currently uses AdministratorAccess)
- [ ] Remote state backend (S3 + DynamoDB locking)
- [ ] Terraform variables for source IP instead of hardcoded /32
- [ ] Multi-node k3s
- [ ] Terraform mirror against OpenStack provider

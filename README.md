# external-secrets-rancher-store-operator

This Kubernetes Operator creates a `ClusterSecretStore` for 
[External Secrets Operator](https://external-secrets.io/latest/provider/kubernetes/), for all namespaces in every cluster managed by
the Rancher server, including the cluster `local` itself.

The `ClusterSecretStore`'s are named `cluster-{{ clusterName }}-{{ namespace }}`.
The prefix cannot be configured currently.

# Filter Namespaces

In the values.yaml you need configure the namespaces that should be replicated using regex filters. The first match in
cluster will be used to filter the namespaces:

```yaml
namespaces:
  - clusterName: local
    namespaces:
      - fleet-.*
  - clusterName: .*
    namespaces:
      - default
```

# Why should I use it?

Managing secrets with tools like External Secrets Operator always results in a chicken and egg problem. The first
secret store that needs to be configured, requires secrets himself to connect.

As I manage all my Kubernetes clusters with Rancher, my solution for this problem is, to provide my Clusters with this
initial secrets from the rancher server itself using a
[PushSecret](https://external-secrets.io/latest/provider/kubernetes/#pushsecret).

This project solves the problem of allowing managing the required secret stores manually for all the clusters.

# Installation 

## Dependencies

This project is meant to be installed into a Rancher cluster, and requires
[External Secrets Operator](https://metacontroller.github.io/metacontroller/guide/helm-install.html) to be installed.
It is build using `metacontroller`, and need to have
[Metacontroller](https://metacontroller.github.io/metacontroller/guide/helm-install.html) installed as well.

## Helm

**The required dependencies of this project, are not part of the Helm Chart!**

Install the helm Chart in this repository to your Rancher cluster. If you are using fleet, you can install the Helm
chart with this `fleet.yaml`.

```yaml
defaultNamespace: external-secrets-rso

helm:
  chart: git::https://github.com/Deltachaos/external-secrets-rancher-store-operator//helm/external-secrets-rancher-store-operator?ref=main
  version: 0.1.0
```

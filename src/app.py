from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import yaml
from re import L
import kubernetes
from io import StringIO
import os
import re

class Controller(BaseHTTPRequestHandler):
  def matchesFilter(self, cluster, namespace):
    namespaceFilter = json.loads(os.environ['NAMESPACES'])

    for clusterFilter in namespaceFilter:
        patternCluster = re.compile(clusterFilter["clusterName"])
        if patternCluster.match(cluster):
            for filter in clusterFilter["namespaces"]:
                patternNamespace = re.compile(clusterFilter["clusterName"])
                if patternNamespace.match(namespace):
                    return True

            return False

    return False

  def sync(self, parent, children):
    desired_status = {
      "clustersecretstores": len(children["ClusterSecretStore.external-secrets.io/v1beta1"]),
      "configmaps": len(children["ConfigMap.v1"]),
    }
    prefix = "rso-"
    prefixStore = "cluster-"

    kubeconfig = yaml.safe_load(base64.b64decode(parent["data"]["value"]).decode("utf-8"))

    configuration = kubernetes.client.Configuration()
    loader = kubernetes.config.kube_config.KubeConfigLoader(kubeconfig)
    loader.load_and_set(configuration)
    api_client=kubernetes.client.ApiClient(configuration)
    v1 = kubernetes.client.CoreV1Api(api_client)
    namespaces = v1.list_namespace()

    kubernetesServer = kubeconfig["clusters"][0]["cluster"]["server"]
    kubernetesCa = base64.b64decode(kubeconfig["clusters"][0]["cluster"]["certificate-authority-data"]).decode("utf-8")

    kubeconfigName = parent["metadata"]["name"]
    clusterNamespace = parent["metadata"]["namespace"]
    clusterName = parent["metadata"]["labels"]["cluster.x-k8s.io/cluster-name"]
    desired_resources = [
      {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
          "name": prefix + clusterName + "-kube-root-ca.crt",
          "namespace": clusterNamespace
        },
        "data": {
          "ca.crt": kubernetesCa
        }
      }
    ]

    for ns in namespaces.items:
      if not self.matchesFilter(clusterName, ns.metadata.name):
          print(f"Skip namespace: {ns.metadata.name}")
          continue

      print(f"Add namespace: {ns.metadata.name}")

      desired_resources.append({
        "apiVersion": "external-secrets.io/v1beta1",
        "kind": "ClusterSecretStore",
        "metadata": {
          "name": prefixStore + clusterName + "-" + ns.metadata.name
        },
        "spec": {
          "provider": {
            "kubernetes": {
              "remoteNamespace": ns.metadata.name,
              "auth": {
                "token": {
                  "bearerToken": {
                    "key": "token",
                    "name": kubeconfigName,
                    "namespace": clusterNamespace
                  }
                }
              },
              "server": {
                "caProvider": {
                  "key": "ca.crt",
                  "name": prefix + clusterName + "-kube-root-ca.crt",
                  "namespace": clusterNamespace,
                  "type": "ConfigMap"
                },
                "url": kubernetesServer
              }
            }
          }
        }
      })

    return {"status": desired_status, "attachments": desired_resources}

  def do_POST(self):
    observed = json.loads(self.rfile.read(int(self.headers.get("content-length"))))
    print(observed)
    desired = self.sync(observed["object"], observed["attachments"])
    print("desired")
    print(desired)

    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(desired).encode())

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps({"status": "ok"}).encode())

print("Listen on port 8080")
HTTPServer(("", 8080), Controller).serve_forever()
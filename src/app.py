from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import yaml
from re import L
from kubernetes.config.kube_config import KubeConfigLoader
from kubernetes import client, config
from io import StringIO

class Controller(BaseHTTPRequestHandler):
  def sync(self, parent, children):
    desired_status = {
      "clustersecretstores": len(children["ClusterSecretStore.external-secrets.io/v1beta1"]),
      "configmaps": len(children["ConfigMap.v1"]),
    }
    prefix = "rso-"
    prefixStore = "cluster-"

    kubeconfig = yaml.safe_load(base64.b64decode(parent["data"]["value"]).decode("utf-8"))

    loader = KubeConfigLoader(kubeconfig)
    config = client.Configuration()
    loader.load_and_set(config)
    client.Configuration.set_default(config)

    v1 = client.CoreV1Api()
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
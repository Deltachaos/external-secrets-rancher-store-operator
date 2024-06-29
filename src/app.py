from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import yaml
from re import L

class Controller(BaseHTTPRequestHandler):
  def sync(self, parent, children):
    desired_status = {
      "clustersecretstores": len(children["ClusterSecretStore.external-secrets.io/v1beta1"]),
      "configmaps": len(children["ConfigMap.v1"]),
    }
    prefix = "rso-"
    kubeconfig = base64.b64decode(parent["data"]["value"]).decode("utf-8")
    print(kubeconfig)
    kubeconfigName = parent["metadata"]["name"]
    clusterNamespace = parent["metadata"]["namespace"]
    clusterName = parent["metadata"]["labels"]["cluster.x-k8s.io/cluster-name"]
    desired_resources = [
      {
        "apiVersion": "external-secrets.io/v1beta1",
        "kind": "ClusterSecretStore",
        "metadata": {
          "name": prefix + clusterName
        },
        "spec": {
          "provider": {
            "kubernetes": {
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
                "url": "https://10.43.220.193/k8s/clusters/c-m-kpfqd4s2"
              }
            }
          }
        }
      },
      {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
          "name": prefix + clusterName + "-kube-root-ca.crt",
          "namespace": clusterNamespace
        },
        "data": {
          "ca.crt": "-----BEGIN CERTIFICATE-----\nMIIBvjCCAWOgAwIBAgIBADAKBggqhkjOPQQDAjBGMRwwGgYDVQQKExNkeW5hbWlj\nbGlzdGVuZXItb3JnMSYwJAYDVQQDDB1keW5hbWljbGlzdGVuZXItY2FAMTcxOTQy\nOTI4MTAeFw0yNDA2MjYxOTE0NDFaFw0zNDA2MjQxOTE0NDFaMEYxHDAaBgNVBAoT\nE2R5bmFtaWNsaXN0ZW5lci1vcmcxJjAkBgNVBAMMHWR5bmFtaWNsaXN0ZW5lci1j\nYUAxNzE5NDI5MjgxMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEHlGspFAnxLYa\nj/Nlodurwuq3+kvb+j/O/HRn6jqKxqHebnO/0ZCI62ld2jb81kKLG5lJr4fXHl/k\ns/xB5bLuNKNCMEAwDgYDVR0PAQH/BAQDAgKkMA8GA1UdEwEB/wQFMAMBAf8wHQYD\nVR0OBBYEFB4jPxF2IpdNnhfOUaaZ691+dBPeMAoGCCqGSM49BAMCA0kAMEYCIQCf\nr3XMHI4p8AM3qGCedkCuOU3T2j/2wCymITnFBF8drwIhAPd6fqMYWRQzBua2anrU\nEL1cz3d5MH4ziXiIVQOmfjGG\n-----END CERTIFICATE-----\n"
        }
      }
    ]

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
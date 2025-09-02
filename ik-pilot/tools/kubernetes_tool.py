import os
from typing import Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

def _load_config():
    kc = os.getenv("KUBECONFIG")
    try:
        if kc and os.path.exists(os.path.expanduser(kc)):
            config.load_kube_config(os.path.expanduser(kc))
        else:
            # try in-cluster, then default
            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
    except Exception as e:
        raise RuntimeError(f"Kubernetes config error: {e}")

class KubernetesTool:
    name = "kubernetes"
    description = "Operate Kubernetes: list pods, get logs, rollout restart deployment."

    def __init__(self):
        _load_config()

    async def invoke(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "list_pods":
            return self.list_pods(params.get("namespace", "default"), params.get("label_selector"))
        if action == "get_logs":
            return self.get_logs(params["namespace"], params["name"], params.get("container"), params.get("tail_lines", 200))
        if action == "rollout_restart":
            return self.rollout_restart(params["namespace"], params["deployment"])
        raise ValueError(f"Unsupported action: {action}")

    def list_pods(self, namespace: str, label_selector: str = None) -> Dict[str, Any]:
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items
        data = [{"name": p.metadata.name, "phase": p.status.phase, "node": p.spec.node_name} for p in pods]
        return {"namespace": namespace, "count": len(data), "pods": data}

    def get_logs(self, namespace: str, name: str, container: str = None, tail_lines: int = 200) -> Dict[str, Any]:
        v1 = client.CoreV1Api()
        logs = v1.read_namespaced_pod_log(name=name, namespace=namespace, container=container, tail_lines=tail_lines)
        return {"namespace": namespace, "name": name, "container": container, "tail": tail_lines, "logs": logs[-4000:]}

    def rollout_restart(self, namespace: str, deployment: str) -> Dict[str, Any]:
        apps = client.AppsV1Api()
        body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": client.rest.datetime.datetime.utcnow().isoformat()}}}}}
        try:
            apps.patch_namespaced_deployment(name=deployment, namespace=namespace, body=body)
            return {"namespace": namespace, "deployment": deployment, "status": "restarted"}
        except ApiException as e:
            return {"error": e.reason, "status": e.status, "body": e.body}

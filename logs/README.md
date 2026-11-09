# 调度日志证据（关键片段）

W1 的 T0-1 / T0-2 用到的调度日志。完整日志体积较大（`07-scheduler-v5-full.log` 约 190KB，`01/02` 各约 150KB），未提交，可用下面的命令重新采集。

| 文件 | 用途 |
|---|---|
| `03-scheduler-v5-nginx-demo-window.log` | `nginx-demo` 在 v=5 下的完整调度窗口（成功路径） |
| `04-scheduler-v10-nginx-demo-v10.log` | 临时调到 v=10 后的插件打分日志 |
| `05-nginx-demo-describe.txt` | `nginx-demo` 的 describe，含 Scheduling 事件 |
| `06-kube-scheduler-manifest.yaml` | kube-scheduler 静态 Pod 清单（`--v=5`） |
| `08-scheduler-v5-nginx-big-unschedulable.log` | `nginx-big` 两次 FailedScheduling（间隔 5 分钟） |
| `09-nginx-big-pod-describe.txt` | `nginx-big` 的 Pending 事件 |
| `10-nginx-big-deploy-describe.txt` | `nginx-big` Deployment 的 describe |

## 环境

- kind 集群 `wpk8s`，单 control-plane 节点，Kubernetes v1.32.0
- kube-scheduler 启动参数：`--v=5 --leader-elect=true`
- 日志时区：UTC（比本机 CST 慢 8 小时）

## 重新采集

```bash
# 全量日志
kubectl logs -n kube-system kube-scheduler-wpk8s-control-plane --timestamps

# 只看某个 Pod
kubectl logs -n kube-system kube-scheduler-wpk8s-control-plane | grep 'pod="default/nginx-demo"'

# 事件
kubectl describe pod nginx-demo

# 静态 Pod 清单
docker exec wpk8s-control-plane cat /etc/kubernetes/manifests/kube-scheduler.yaml
```

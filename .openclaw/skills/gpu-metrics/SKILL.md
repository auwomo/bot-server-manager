---
name: gpu-metrics
description: |
  Use when user asks about GPU usage, training jobs, cluster health, temperature,
  power, scheduling/queue status, or requests a periodic cluster report.
  Covers two clusters: DiGua cloud (288×H20, K8s/Volcano) and School HPC (~480×H800/H100, SLURM).
---

# GPU 集群监控（多集群）

两个 GPU 训练集群的实时监控，数据存储在 VictoriaMetrics 时序数据库。

## 命令

```bash
gpu-metrics [--cluster digua|school|all] <subcommand> [--format json]
```

| 子命令 | 作用 |
|--------|------|
| `report` | 完整状态报告（适合飞书群发） |
| `summary` | 总览：总数/分配/空闲/利用率 |
| `jobs` | 运行中的训练任务 |
| `queue` | 调度队列/分区状态 |
| `errors` | 故障检测：XID/行重映射/PCIe |
| `utilization` | 利用率详情：Tensor Core/SM/分布 |
| `temperature` | 温度：核心/显存/超温统计 |
| `power` | 功耗：总/节点/单卡 |
| `nodes` | 每节点状态 |
| `network` | NVLink / InfiniBand |
| `storage` | GPFS 存储（仅 DiGua） |
| `query "<PromQL>"` | 自定义 PromQL 查询 |

默认 `--cluster digua`。使用 `--cluster school` 查询学校集群，`--cluster all` 查询全部。

## 场景映射

| 用户问题 | 命令 |
|----------|------|
| "集群现在什么情况" / "GPU 汇报" | `gpu-metrics report` |
| "学校集群利用率怎么样" | `gpu-metrics --cluster school summary` |
| "还有多少空闲卡" / "能跑几张卡的任务" | `gpu-metrics summary` |
| "谁在跑任务" / "实验室谁在用 GPU" | `gpu-metrics --cluster school jobs` |
| "SLURM 排队了吗" / "学校集群能提交吗" | `gpu-metrics --cluster school queue` |
| "地瓜云队列排队了吗" | `gpu-metrics queue` |
| "所有集群什么情况" | `gpu-metrics --cluster all report` |
| "集群有没有故障" / "哪些卡有问题" | `gpu-metrics errors` |
| "利用率怎么样" / "有没有卡在空跑" | `gpu-metrics utilization` |
| "温度正常吗" / "有没有过热" | `gpu-metrics temperature` |

## 集群概况

**DiGua (digua)** — 36 节点 × 8 GPU = 288 张 NVIDIA H20，K8s + Volcano 调度，InfiniBand + GPFS。

**School HPC (school)** — ~60 节点 (~480 张 H800/H100)，SLURM 调度，9 个按实验室划分的分区。DCGM 指标自带 `hpc_job` 标签可关联到 SLURM 任务。

## 输出格式

- `report` 文本输出含 emoji 分节（📊📋⚠️🌡️），适合直接发飞书群
- `--format json` 返回结构化数据，可进一步分析
- 学校集群的 `jobs` 显示 user/partition/job_name（非 pod/namespace）

## 注意事项

- 数据实时性：DiGua ~15-30s（remote_write），School ~30s（采集器推送间隔）
- "已分配" 含义不同：DiGua = K8s pod resource requests，School = SLURM GRES 分配
- 学校集群部分节点可能无 DCGM 数据（节点 down 或 exporter 未运行）

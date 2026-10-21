# HW3: CPU Scheduler Simulator

Name: Muhammed Raees Nasar

## 1. Overview

simulator.py runs FCFS, SJF, Round Robin, Priority, and MLFQ. It returns which process runs and when, then calculates average waiting, turnaround, and response times.

## 2. Results

# Workload 1: "sample.csv"

Four processes (P1 = 6, P2 = 2, P3 = 8, P4 = 3), all arriving at time 0.

| Algorithm | Avg Waiting | Avg Turnaround | Avg Response |

| FCFS |.      7.50 |            12.25 |       7.50 |
| SJF |        4.50 |           9.25   |         4.50 |
| Round Robin | 8.50 |         13.25   |        5.00 |
| Priority |    9.00 |         13.75   |         9.00 |
| MLFQ |        8.50 |         13.25 |           5.00 |

# Workload 2: my_workload.csv

Seven processes with different arrival times, an idle gap, and a long process (P6, burst 25).

| Algorithm | Avg Waiting | Avg Turnaround | Avg Response |

| FCFS | 10.71 | 19.57 | 10.71 |
| SJF | 7.00 | 15.86 | 7.00 |
| Round Robin | 10.71 | 19.57 | 3.86 |
| Priority | 7.00 | 15.86 | 7.00 |
| MLFQ | 10.29 | 19.14 | 3.86 |

# 3. Analysis

SJF had the lowest average waiting and turnaround times in both workloads because it runs shorter jobs first. Round Robin and MLFQ had lower response times since processes get CPU time sooner. Priority depends on how the priorities are assigned. MLFQ did slightly better than Round Robin on Workload 2 because shorter jobs can finish in higher queues.

## 4. Scheduling Rules

- **FCFS/SJF:** Non-preemptive.
- **Round Robin:** Quantum of 4. New arrivals are queued before the process that just ran.
- **Priority:** Non-preemptive; lower number means higher priority. Aging improves priority for processes that wait.
- **MLFQ:** Three queues with quanta 4, 8, and 16. Processes move down when they use their full quantum. Every 50 time units, they are boosted back to Q0.
- **General:** Ties use arrival time, then input order. If no process is ready, the CPU waits for the next arrival.

## 5. How to Run

```
python3 simulator.py --workload sample.csv --algo fcfs
python3 simulator.py --workload sample.csv --compare
python3 simulator.py --workload my_workload.csv --compare
```


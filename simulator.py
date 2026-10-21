#!/usr/bin/env python3


import argparse
import copy
import csv
import sys
from collections import deque


# Process info
class SimProcess:
    def __init__(self, pid, arrival_time, burst_time, priority=0, order=0):
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.remaining_time = burst_time  # time left
        self.priority = priority
        self.order = order                # tie-break order
        self.start_time = None            # first run
        self.completion_time = None


# Load the CSV
def load_workload(path):
    procs = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip() or row[0].strip().startswith("#"):
                continue
            if row[0].strip().lower() == "pid":
                continue
            pid = row[0].strip()
            arrival = int(row[1])
            burst = int(row[2])
            priority = int(row[3]) if len(row) > 3 and row[3].strip() else 0
            procs.append(SimProcess(pid, arrival, burst, priority, order=len(procs)))
    return procs


# Sort by arrival
def _by_arrival(processes):
    return sorted(processes, key=lambda p: (p.arrival_time, p.order))


# Scheduling algorithms

def _non_preemptive(processes, key):
    """Pick a ready process and run it to the end."""
    pending = _by_arrival(processes)
    segments = []
    t = 0
    while pending:
        ready = [p for p in pending if p.arrival_time <= t]
        if not ready:
            t = pending[0].arrival_time  # wait for next arrival
            continue
        p = min(ready, key=lambda p: key(p, t))
        pending.remove(p)
        segments.append((p.pid, t, t + p.burst_time))
        t += p.burst_time
        p.remaining_time = 0
    return segments


def fcfs_schedule(processes, quantum=None):
    return _non_preemptive(processes, lambda p, t: (p.arrival_time, p.order))


def sjf_schedule(processes, quantum=None):
    return _non_preemptive(
        processes, lambda p, t: (p.burst_time, p.arrival_time, p.order))


def priority_schedule(processes, quantum=None, aging_interval=5):
    def key(p, t):
        waited = t - p.arrival_time
        effective = p.priority - (waited // aging_interval)
        return (effective, p.arrival_time, p.order)
    return _non_preemptive(processes, key)


def round_robin_schedule(processes, quantum=None):
    quantum = quantum or 4
    pending = _by_arrival(processes)
    n = len(pending)
    i = 0
    ready = deque()
    segments = []
    t = 0
    while i < n or ready:
        if not ready:
            t = max(t, pending[i].arrival_time)
        while i < n and pending[i].arrival_time <= t:
            ready.append(pending[i])
            i += 1
        p = ready.popleft()
        run = min(quantum, p.remaining_time)
        segments.append((p.pid, t, t + run))
        t += run
        p.remaining_time -= run
        while i < n and pending[i].arrival_time <= t:  # add new arrivals
            ready.append(pending[i])
            i += 1
        if p.remaining_time > 0:  # requeue if unfinished
            ready.append(p)
    return segments


def mlfq_schedule(processes, quantum=None, quanta=(4, 8, 16),
                  boost_interval=50, log=None):
    if quantum:
        quanta = (quantum, quantum * 2, quantum * 4)
    levels = len(quanta)
    queues = [deque() for _ in quanta]
    pending = _by_arrival(processes)
    n = len(pending)
    i = 0
    t = 0
    next_boost = boost_interval
    segments = []

    def admit(upto):
        nonlocal i
        while i < n and pending[i].arrival_time <= upto:
            queues[0].append(pending[i])
            i += 1

    while i < n or any(queues):
        admit(t)
        if not any(queues):
            t = pending[i].arrival_time  # wait for next arrival
            continue

        if t >= next_boost:  # boost queues
            moved = False
            for lvl in range(1, levels):
                while queues[lvl]:
                    queues[0].append(queues[lvl].popleft())
                    moved = True
            if moved and log is not None:
                log.append((t, "-", "-", "Priority boost: all processes back to Q0"))
            next_boost = (t // boost_interval + 1) * boost_interval

        lvl = next(k for k in range(levels) if queues[k])
        p = queues[lvl].popleft()
        q = quanta[lvl]
        run = min(q, p.remaining_time)
        segments.append((p.pid, t, t + run))
        start = t
        t += run
        p.remaining_time -= run
        admit(t)

        if p.remaining_time == 0:
            action = f"Finishes at t={t}"
        elif lvl < levels - 1:
            queues[lvl + 1].append(p)
            action = f"Runs full quantum ({q}) -> demoted to Q{lvl + 1}"
        else:
            queues[lvl].append(p)
            action = f"Runs full quantum ({q}) -> stays in Q{lvl} (lowest queue)"
        if log is not None:
            log.append((start, p.pid, f"Q{lvl}", action))
    return segments


# Timing calculations

# Get each process's times
def compute_metrics(processes, segments):
    """Calculate each process's times."""
    first, last = {}, {}
    for pid, s, e in segments:
        first.setdefault(pid, s)
        last[pid] = e
    rows = []
    for p in processes:
        p.start_time = first[p.pid]
        p.completion_time = last[p.pid]
        turnaround = p.completion_time - p.arrival_time
        rows.append({
            "p": p,
            "start": p.start_time,
            "completion": p.completion_time,
            "turnaround": turnaround,
            "waiting": turnaround - p.burst_time,
            "response": p.start_time - p.arrival_time,
        })
    rows.sort(key=lambda r: (r["start"], r["p"].order))
    return rows


def averages(rows):
    n = len(rows)
    return (sum(r["waiting"] for r in rows) / n,
            sum(r["turnaround"] for r in rows) / n,
            sum(r["response"] for r in rows) / n)


ALGOS = {
    "fcfs": ("FCFS", fcfs_schedule),
    "sjf": ("SJF", sjf_schedule),
    "rr": ("Round Robin", round_robin_schedule),
    "priority": ("Priority", priority_schedule),
    "mlfq": ("MLFQ", mlfq_schedule),
}


def run_algo(key, workload, quantum=None, log=None):
    procs = copy.deepcopy(workload)  # fresh copy
    fn = ALGOS[key][1]
    if key == "mlfq":
        segments = fn(procs, quantum, log=log)
    else:
        segments = fn(procs, quantum)
    return compute_metrics(procs, segments)


# Printing the results

# Print a table
def print_table(rows, show_priority=False):
    head = f"{'PID':<6}{'Arrival':<9}{'Burst':<7}"
    if show_priority:
        head += f"{'Priority':<10}"
    head += f"{'Start':<7}{'Completion':<12}{'Waiting':<9}{'Turnaround':<12}{'Response'}"
    print(head)
    for r in rows:
        p = r["p"]
        line = f"{p.pid:<6}{p.arrival_time:<9}{p.burst_time:<7}"
        if show_priority:
            line += f"{p.priority:<10}"
        line += (f"{r['start']:<7}{r['completion']:<12}{r['waiting']:<9}"
                 f"{r['turnaround']:<12}{r['response']}")
        print(line)
    w, t, r = averages(rows)
    print(f"Average Waiting Time:    {w:.2f}")
    print(f"Average Turnaround Time: {t:.2f}")
    print(f"Average Response Time:   {r:.2f}")


def print_mlfq_log(log):
    print(f"{'Time':<7}{'PID':<6}{'Queue':<8}Action")
    for time, pid, queue, action in log:
        print(f"{time:<7}{pid:<6}{queue:<8}{action}")


def print_compare(workload, quantum):
    print(f"{'Algorithm':<15}{'Avg Waiting':<13}{'Avg Turnaround':<16}{'Avg Response'}")
    for key, (name, _) in ALGOS.items():
        w, t, r = averages(run_algo(key, workload, quantum))
        print(f"{name:<15}{w:<13.2f}{t:<16.2f}{r:.2f}")


# Run from the terminal
def main():
    ap = argparse.ArgumentParser(description="CPU scheduler simulator")
    ap.add_argument("--workload", required=True, help="CSV: pid,arrival,burst,priority")
    ap.add_argument("--algo", choices=ALGOS.keys())
    ap.add_argument("--compare", action="store_true", help="run all five and compare")
    ap.add_argument("--quantum", type=int, default=None,
                    help="RR quantum (default 4); MLFQ Q0 quantum (default 4, then x2, x4)")
    args = ap.parse_args()

    if not args.algo and not args.compare:
        ap.error("pick --algo <name> or --compare")

    workload = load_workload(args.workload)
    if not workload:
        sys.exit("workload file has no processes")

    if args.compare:
        print_compare(workload, args.quantum)
        return

    if args.algo == "mlfq":
        log = []
        rows = run_algo("mlfq", workload, args.quantum, log)
        print_mlfq_log(log)
        print()
        print_table(rows)
    else:
        rows = run_algo(args.algo, workload, args.quantum)
        print_table(rows, show_priority=(args.algo == "priority"))


if __name__ == "__main__":
    main()

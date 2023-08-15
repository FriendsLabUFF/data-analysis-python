# importing packages
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import NamedTuple
import datetime as dt
import decimal as dec
import logging
import pandas as pd
from enum import StrEnum

FACTOR = 1_000
SECOND = 1
MILLISECOND = SECOND * FACTOR
MICROSECOND = MILLISECOND * FACTOR


class ProcessStatus(StrEnum):
    D = "uninterruptible sleep"
    I = "idle"
    R = "running"
    S = "sleeping"
    T = "stopped by job control signal"
    t = "stopped by debugger during trace"
    Z = "zombie"

class Process(NamedTuple):
    """Process class.

    Args:
        pid: Process ID
        user: User running the process
        pr: Process priority (kernel)
        ni: Process nice value, priority (user)
        virt: Process virtual memory size (KiB)
        res: Process resident memory size (KiB)
        shr: Process shared memory size (KiB)
        s: Process status
        cpu: Process CPU usage (%)
        mem: Process memory usage (%)
        time: Process total CPU Time
        command: Command used to start the process
    """
    pid: int
    user: str
    pr: int
    ni: int
    virt: int
    res: int
    shr: int
    s: ProcessStatus
    cpu: dec.Decimal
    mem: dec.Decimal
    time: dt.time
    command: str

    @classmethod
    def from_line(cls: "Process", pid: str, user: str, pr: str, ni: str, virt: str, res: str, shr: str, s: str, cpu: str, mem: str, time: str, command: str) -> "Process":
        i_pid = int(pid)
        i_pr = int(pr)
        i_ni = int(ni)
        i_virt = int(virt)
        i_res = int(res)
        i_shr = int(shr)
        ps_s = ProcessStatus[s]
        d_cpu = dec.Decimal(cpu.replace(",", "."))
        d_mem = dec.Decimal(mem.replace(",", "."))
        minutes, seconds = time.split(":")
        f_seconds = float(seconds)
        i_minutes = int(minutes)
        i_seconds = int(f_seconds)
        i_microsecond = int((f_seconds % 1) * MICROSECOND)
        t_time = dt.time(minute=i_minutes, second=i_seconds, microsecond=i_microsecond)
        return cls(pid=i_pid, user=user, pr=i_pr, ni=i_ni, virt=i_virt, res=i_res, shr=i_shr, s=ps_s, cpu=d_cpu, mem=d_mem, time=t_time, command=command)


class Top(NamedTuple):
    pid: int
    user: str
    command: str
    pr_list: list[int] = []
    ni_list: list[int] = []
    virt_list: list[int] = []
    res_list: list[int] = []
    shr_list: list[int] = []
    s_list: list[ProcessStatus] = []
    cpu_list: list[dec.Decimal] = []
    mem_list: list[dec.Decimal] = []
    time_list: list[dt.time] = []


class DB:
    _database: dict[int, Top] = {}

    def append(self: "DB", process: Process) -> None:
        pid = process.pid
        top = self.get(pid)
        if top is None:
            raise SystemError("Top does not exist")
        top.pr_list.append(process.pr)
        top.ni_list.append(process.ni)
        top.virt_list.append(process.virt)
        top.res_list.append(process.res)
        top.shr_list.append(process.shr)
        top.s_list.append(process.s)
        top.cpu_list.append(process.cpu)
        top.mem_list.append(process.mem)
        top.time_list.append(process.time)

    def get(self: "DB", item: int) -> Top | None:
        return self._database.get(item, None)

    def set(self: "DB", top: Top) -> None:
        pid = top.pid
        if self.get(pid) is not None:
            raise SystemError("Top already exists")
        self._database[pid] = top


def process_client(path: Path) -> DB:
    print(f"Processing {path}...")
    db = DB()  # database
    with (path / "top.log").open(encoding="utf8", newline="\n") as log:
        for line in log:
            try:
                process = Process.from_line(*line.split())
            except TypeError as error:
                logging.exception(error)
            else:
                top = db.get(process.pid)
                if top is None:
                    top = Top(pid=process.pid, user=process.user, command=process.command)
                    db.set(top)
                db.append(process)
    return db


root_path = Path("data") / "5g"

for content in root_path.iterdir():
    if content.name == "comtrade":
        continue
    db = process_client(content / "client")

    pidof = {3528: "ptp4l", 3518: "tcpdump", 3523: "tcpdump", 2678: "poetry"}
    # pid = 3528  # ptp4l
    # pid = 3518  # tcpdump
    # pid = 3523  # tcpdump
    # pid = 2678  # poetry

    # Virtual MEM by Process
    # TODO *_list is holding ALL data (not only the specific process data)
    virts = []
    for pid in db._database.keys():
        virt = pd.DataFrame(db.get(pid).virt_list, columns=[pidof[pid]])
        virts.append(virt)
    process = pd.concat(virts, axis=1)
    dfm = process.melt(var_name='Process', value_name='Virtual memory size (KiB)', ignore_index=False)
    sns.lineplot(x=dfm.index, y="Virtual memory size (KiB)", hue='Process', data=dfm)

    # # CPU x MEM Percentage
    # process_cpu = pd.DataFrame(db.get(pid).cpu_list, columns=['cpu'])
    # process_mem = pd.DataFrame(db.get(pid).mem_list, columns=['mem'])
    # process = process_cpu.merge(process_mem, left_index=True, right_index=True)
    # dfm = process.melt(var_name='type', value_name='percentage', ignore_index=False)
    # sns.lineplot(x=dfm.index, y="percentage", hue='type', data=dfm).set(title=f"{pid}: {pidof[pid]}")

    # # Priority
    # process_pr = pd.DataFrame(db.get(pid).pr_list, columns=['pr'])
    # process_ni = pd.DataFrame(db.get(pid).ni_list, columns=['ni'])
    # process = process_pr.merge(process_ni, left_index=True, right_index=True)
    # dfm = process.melt(var_name='type', value_name='value', ignore_index=False)
    # sns.lineplot(x=dfm.index, y="value", hue='type', data=dfm).set(title=f"{pid}: {pidof[pid]}")

    # # Memory
    # process_virt = pd.DataFrame(db.get(pid).virt_list, columns=['virt'])
    # process_res = pd.DataFrame(db.get(pid).res_list, columns=['res'])
    # process_shr = pd.DataFrame(db.get(pid).shr_list, columns=['shr'])
    # process = process_virt.merge(process_res, left_index=True, right_index=True)
    # process = process.merge(process_shr, left_index=True, right_index=True)
    # dfm = process.melt(var_name='type', value_name='KiB', ignore_index=False)
    # sns.lineplot(x=dfm.index, y="KiB", hue='type', data=dfm).set(title=f"{pid}: {pidof[pid]}")

    # # Status
    # process = pd.DataFrame(db.get(pid).s_list, columns=['status'])
    # sns.lineplot(x=process.index, y=process.status).set(title=f"{pid}: {pidof[pid]}")

    # # Total CPU Time
    # process = pd.DataFrame(db.get(pid).time_list, columns=['time'])
    # process = process.applymap(lambda x: ((x.hour*60+x.minute)*60+x.second)*10**6+x.microsecond)
    # sns.lineplot(x=process.index, y=process.time).set(title=f"{pid}: {pidof[pid]}")

    # process = db.get(pid)
    # for cpu, mem, time in zip(process.cpu_list, process.mem_list, process.time_list):
    #     print(cpu, mem, time)
    # exit()

    plt.show()
    break

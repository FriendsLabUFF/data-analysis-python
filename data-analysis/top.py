# importing packages
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import NamedTuple
import datetime as dt
import decimal as dec
import logging
import pandas as pd
from enum import Enum

FACTOR = 1_000
SECOND = 1
MILLISECOND = SECOND * FACTOR
MICROSECOND = MILLISECOND * FACTOR
EXTENSION = '.png'


class ProcessStatus(Enum):
    D = "uninterruptible sleep"
    I = "idle"  # noqa: E741
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
    def from_line(
        cls: "Process",
        pid: str,
        user: str,
        pr: str,
        ni: str,
        virt: str,
        res: str,
        shr: str,
        s: str,
        cpu: str,
        mem: str,
        time: str,
        command: str,
    ) -> "Process":
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
        return cls(
            pid=i_pid,
            user=user,
            pr=i_pr,
            ni=i_ni,
            virt=i_virt,
            res=i_res,
            shr=i_shr,
            s=ps_s,
            cpu=d_cpu,
            mem=d_mem,
            time=t_time,
            command=command.replace('python3', 'pd_client'),
        )


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

    @classmethod
    def from_process(cls: "Top", process: "Process") -> "Top":
        return Top(
            pid=process.pid,
            user=process.user,
            pr_list=[process.pr],
            ni_list=[process.ni],
            virt_list=[process.virt],
            res_list=[process.res],
            shr_list=[process.shr],
            s_list=[process.s],
            cpu_list=[process.cpu],
            mem_list=[process.mem],
            time_list=[process.time],
            command=process.command,
        )


class DB:

    def __init__(self: "DB") -> None:
        self._database: dict[int, Top] = {}

    def pidof(self: "DB") -> dict[int, str]:
        pids: dict[int, str] = {}
        for pid, process in self._database.items():
            pids[pid] = process.command
        return pids

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


def process_top(path: Path) -> DB:
    print(f"Processing {path}...")
    db = DB()  # database
    count = 0

    if (path / "top.log").exists():
        filepath = path / "top.log"
    else:
        filepath = path / "top.txt"

    with filepath.open(encoding="utf8", newline="\n") as log:
        for line in log:
            count += 1
            process = Process.from_line(*line.split())
            top = db.get(process.pid)
            if top is None:
                top = Top.from_process(process)
                db.set(top)
            db.append(process)
    return db


def plot_virtual_mem(db: DB, pidof: dict[int, str], name: str, path: Path) -> None:
    # Virtual MEM by Process
    virts = []
    for pid in pidof.keys():
        virt = pd.DataFrame(db.get(pid).virt_list, columns=[f"{pid} [{pidof[pid]}]"])
        virts.append(virt)
    process = pd.concat(virts, axis=1)
    dfm = process.reset_index().melt(
        id_vars="index", var_name="Process", value_name="Virtual memory size (KiB)",
    )

    plt.figure()
    sns.lineplot(x="index", y="Virtual memory size (KiB)", hue="Process", data=dfm).set(title=name)
    new_path = path.parent / '01 Virtual Memory by Host'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + EXTENSION))
    # plt.show()
    plt.close()


def plot_cpu_x_mem(db: DB, pidof: dict[int, str], pid: int, name: str, path: Path) -> None:
    # CPU x MEM Percentage
    process_cpu = pd.DataFrame(db.get(pid).cpu_list, columns=['cpu'])
    process_mem = pd.DataFrame(db.get(pid).mem_list, columns=['mem'])
    process = process_cpu.merge(process_mem, left_index=True, right_index=True)
    dfm = process.melt(var_name='type', value_name='percentage', ignore_index=False)

    process_name = pidof[pid]
    plt.figure()
    sns.lineplot(x=dfm.index, y="percentage", hue="type", data=dfm).set(
        title=f"{name} = {pid} [{process_name}]"
    )
    new_path = path.parent / '02 CPU x Memory by Process'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + f'-{process_name}_{pid}' + EXTENSION))
    # plt.show()
    plt.close()


def plot_priority(db: DB, pidof: dict[int, str], pid: int, name: str, path: Path) -> None:
    # Priority
    process_pr = pd.DataFrame(db.get(pid).pr_list, columns=['pr'])
    process_ni = pd.DataFrame(db.get(pid).ni_list, columns=['ni'])
    process = process_pr.merge(process_ni, left_index=True, right_index=True)
    dfm = process.melt(var_name='type', value_name='value', ignore_index=False)

    process_name = pidof[pid]
    plt.figure()
    sns.lineplot(x=dfm.index, y="value", hue="type", data=dfm).set(
        title=f"{name} = {pid} [{process_name}]"
    )
    new_path = path.parent / '03 Priority by Process'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + f'-{process_name}_{pid}' + EXTENSION))
    # plt.show()
    plt.close()


def plot_memory(db: DB, pidof: dict[int, str], pid: int, name: str, path: Path) -> None:
    # Memory
    process_virt = pd.DataFrame(db.get(pid).virt_list, columns=['virt'])
    process_res = pd.DataFrame(db.get(pid).res_list, columns=['res'])
    process_shr = pd.DataFrame(db.get(pid).shr_list, columns=['shr'])
    process = process_virt.merge(process_res, left_index=True, right_index=True)
    process = process.merge(process_shr, left_index=True, right_index=True)
    dfm = process.melt(var_name='type', value_name='KiB', ignore_index=False)

    process_name = pidof[pid]
    plt.figure()
    sns.lineplot(x=dfm.index, y="KiB", hue="type", data=dfm).set(
        title=f"{name} = {pid} [{pidof[pid]}]"
    )
    new_path = path.parent / '04 Memory by Process'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + f'-{process_name}_{pid}' + EXTENSION))
    # plt.show()
    plt.close()


def plot_status(db: DB, pidof: dict[int, str], pid: int, name: str, path: Path) -> None:
    # Status
    # TODO bad code, improve it
    status_list = db.get(pid).s_list
    status_name_list = []
    for status in db.get(pid).s_list:
        status_name_list.append(f"{status.name}: {status.value}")
    process = pd.DataFrame(status_name_list, columns=['status'])

    process_name = pidof[pid]
    plt.figure()
    sns.lineplot(x=process.index, y=process.status).set(
        title=f"{name} = {pid} [{pidof[pid]}]"
    )
    new_path = path.parent / '05 Status by Process'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + f'-{process_name}_{pid}' + EXTENSION))
    # plt.show()
    plt.close()


def plot_cpu_time(db: DB, pidof: dict[int, str], pid: int, name: str, path: Path) -> None:
    # Total CPU Time
    process = pd.DataFrame(db.get(pid).time_list, columns=['CPU Time (s)'])
    process = process.applymap(
        lambda x: ((x.hour * 60 + x.minute) * 60 + x.second) + (x.microsecond / 10**6)
    )

    process_name = pidof[pid]
    plt.figure()
    sns.lineplot(x=process.index, y=process['CPU Time (s)']).set(
        title=f"{name} = {pid} [{pidof[pid]}]"
    )
    new_path = path.parent / '06 CPU Time by Process'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + f'-{process_name}_{pid}' + EXTENSION))
    # plt.show()
    plt.close()


def plot_cpu_time_by_host(db: DB, pidof: dict[int, str], name: str, path: Path) -> None:
    # Virtual MEM by Process
    cpu_times = []
    for pid in pidof.keys():
        cpu_time = pd.DataFrame(db.get(pid).time_list, columns=[f"{pid} [{pidof[pid]}]"])
        cpu_time = cpu_time.applymap(
            lambda x: ((x.hour * 60 + x.minute) * 60 + x.second) + (x.microsecond / 10 ** 6)
        )
        cpu_times.append(cpu_time)
    process = pd.concat(cpu_times, axis=1)
    dfm = process.reset_index().melt(
        id_vars="index", var_name="Process", value_name='CPU Time (s)',
    )

    plt.figure()
    sns.lineplot(x="index", y='CPU Time (s)', hue="Process", data=dfm).set(title=name)
    new_path = path.parent / '07 CPU Time (s) by Host'
    new_path.mkdir(exist_ok=True)
    plt.savefig(new_path / (path.name + EXTENSION))
    # plt.show()
    plt.close()


def main() -> None:
    root_path = Path("data")
    plots_path = Path('plots')
    plots_path.mkdir(exist_ok=True)

    # sns.set()
    sns.set_palette('coolwarm')

    for experiment_type in root_path.iterdir():
        for content in experiment_type.iterdir():
            if content.name == "comtrade":
                continue
            for host in content.iterdir():
                db = process_top(host)
                pidof = db.pidof()

                pdf_path = plots_path / f'{experiment_type.name}_{content.name}_{host.name}'
                name = f'{experiment_type.name} > {content.name}: {host.name}'

                plot_virtual_mem(db, pidof, name, pdf_path)
                for pid in pidof.keys():
                    plot_cpu_x_mem(db, pidof, pid, name, pdf_path)
                    plot_priority(db, pidof, pid, name, pdf_path)
                    plot_memory(db, pidof, pid, name, pdf_path)
                    plot_status(db, pidof, pid, name, pdf_path)
                    plot_cpu_time(db, pidof, pid, name, pdf_path)
                plot_cpu_time_by_host(db, pidof, name, pdf_path)


if __name__ == "__main__":
    main()

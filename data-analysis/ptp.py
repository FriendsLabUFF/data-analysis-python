import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pathlib import Path

logs_path = Path('plots') / 'ptp'
logs_path.mkdir(exist_ok=True)
dir_path = Path('data')

rc = {
    'figure.figsize': (8, 4),
    'axes.facecolor': 'white',
    'axes.grid': True,
    'grid.color': '.8',
    'font.size': 30}

plt.rcParams.update(rc)

for directory in dir_path.iterdir():
    for folder in directory.iterdir():

        if folder.name == "comtrade":
            continue

        times = []
        ptp_list = []

        with (folder / 'client' / 'ptp.log').open() as log:

            for line in log:
                time, data = line.split(":", 1)

                time = float(time[6:-1])
                data = data.split()

                if not data[0].startswith("master"):
                    continue

                offset_value = int(data[2]) / 1_000  # ns to us
                if offset_value > 1000:
                    continue
                freq_value = int(data[5]) / 1_000  # ns to us

                ptp_list.append([time, offset_value, "Offset"])
                # TODO parts per billion (ppb), meaning???
                # https://access.redhat.com/documentation/pt-br/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-configuring_ptp_using_ptp4l
                ptp_list.append([time, freq_value, "Frequency"])
                times.append(time)

        df_ptp_list = pd.DataFrame(
            ptp_list, columns=["Time (s)", "Synchronism (us)", "Type"]
        )

        sns.set_theme(style="darkgrid")

        sns.relplot(x="Time (s)", y="Synchronism (us)",
                    hue="Type", data=df_ptp_list, linewidth=1,
                    height=6, aspect=18/8, kind="line")

        plt.savefig(logs_path / f"{directory.name}-{folder.name}.png")

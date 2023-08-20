import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set()

log = open("data/5g/01logs/client/ptp.log", "r")

lines = log.readlines()

times = []
ptp_list = []

for line in lines:
    line = line.split(":")
    time = line[0]
    data = line[1]

    time = float(time[6:-2])
    data = data.split()

    if data[0].startswith("master"):
        offset_value = int(data[2])
        freq_value = int(data[5])

        ptp_list.append([time, offset_value, "offset"])
        ptp_list.append([time, freq_value, "freq"])
        times.append(time)

df_ptp_list = pd.DataFrame(ptp_list, columns=["time", "value", "type"])
print(df_ptp_list)

sns.set_theme(style="darkgrid")

sns.lineplot(x="time", y="value", hue="type", data=df_ptp_list)

plt.show()

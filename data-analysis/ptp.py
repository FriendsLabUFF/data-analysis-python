import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

times = []
ptp_list = []

# TODO Executar o open para todos os outros experimentos (for loop)
# TODO Fazer de forma automatica
with open("data/5g/01logs/client/ptp.log", "r") as log:
    for line in log:
        time, data = line.split(":", 1)

        time = float(time[6:-1])
        data = data.split()

        if not data[0].startswith("master"):
            continue

        offset_value = int(data[2]) / 1_000  # ns to us
        if offset_value > 359362165:
            continue
        freq_value = int(data[5]) / 1_000  # ns to us

        ptp_list.append([time, offset_value, "Offset"])
        # TODO parts per billion (ppb), meaning???
        # https://access.redhat.com/documentation/pt-br/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-configuring_ptp_using_ptp4l
        ptp_list.append([time, freq_value, "Frequency"])
        times.append(time)

df_ptp_list = pd.DataFrame(ptp_list, columns=["Time (s)", "Synchronism (us)", "Type"])
# print(df_ptp_list)

sns.set_theme(style="darkgrid")

sns.lineplot(x="Time (s)", y="Synchronism (us)", hue="Type", data=df_ptp_list)

# TODO Mudar para plt.savefig('nome.pdf')
# TODO Preencher as bordas brancas vazias
plt.show()

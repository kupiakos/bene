#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def main():
    plt.style.use('ggplot')
    data = pd.read_csv('delay.csv', header=None, names=('Utilization', 'Average'))
    plt.figure()
    rho = np.linspace(0.01, .99, 100)
    mu = 1. * 10**3 / (1000 * 8)
    delay = (1 / (2 * mu)) * (rho / (1 - rho))
    axis = pd.DataFrame(delay, rho, columns=('Theory',)).plot()
    data.groupby(['Utilization']).mean().plot(ax=axis, style='b.', ylim=(0, 150))
    axis.set_xlabel('Utilization')
    axis.set_ylabel('Delay')
    fig = axis.get_figure()
    fig.set_size_inches(6, 4)
    plt.title('Networking Queuing Delay')
    fig.savefig('queueing.png')


if __name__ == '__main__':
    main()

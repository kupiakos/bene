#!/usr/bin/env python3

import matplotlib.pyplot as plt
plt.style.use('ggplot')


def main():
    windows, speeds, delays = list(zip(*(
        (int(window), float(speed) / 1e6, float(delay) * 1e6)
        for window, speed, delay in (
            line.strip().split(',') for line in open('window-sizes.txt'))
    )))

    plt.figure()
    plt.title('Effect of TCP Window Size on Throughput')
    plt.xlabel('Window Size (bytes)')
    plt.ylabel('Throughput (Mbps)')
    plt.plot(windows, speeds, 'b.-')
    plt.savefig('throughput.png')

    plt.figure()
    plt.title('Effect of TCP Window Size on Queueing Delay')
    plt.xlabel('Window Size (bytes)')
    plt.ylabel('Queueing Delay (μs)')
    plt.plot(windows, delays, 'r.-')
    plt.savefig('queueing.png')

    print('Plots saved!')


if __name__ == '__main__':
    main()

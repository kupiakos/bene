#!/usr/bin/env python3

import os
import argparse
import matplotlib.pyplot as plt
import pandas as pd

plt.style.use('ggplot')
pd.set_option('display.width', 1000)

FIG_SIZE = (11, 5)
MAX_SEC = 5
MSS = 1000
SEQ_MOD = 60

def cwnd(infile, outfile, title=''):
    plt.figure()
    df = pd.read_csv(infile)
    df['Congestion Window'] /= MSS
    df['Threshold'] /= MSS
    ax = df.plot(x="Time", y="Congestion Window", figsize=(8, 5))
    # df.plot(x="Time", y="Threshold", figsize=(8, 5), ax=ax)
    # set the axes
    ax.set_xlabel('Time')
    ax.set_ylabel('Congestion Limit (MSS)')
    plt.suptitle("")
    plt.title(title)
    plt.savefig(outfile)

def sequence(infile, outfile, title=''):
    plt.figure()
    df = pd.read_csv(infile, dtype={'Time': float, 'Sequence Number': int})
    df['Sequence Number'] = df['Sequence Number'] / MSS % SEQ_MOD
    # send
    send = df[df.Event == 'send'].copy()
    ax1 = send.plot(x='Time', y='Sequence Number', kind='scatter', marker='s', s=2, figsize=FIG_SIZE)
    # transmit
    try:
        transmit = df[df.Event == 'transmit'].copy()
        transmit.plot(x='Time', y='Sequence Number', kind='scatter', marker='s', s=2, figsize=FIG_SIZE, ax=ax1)
    except TypeError:
        pass
    # drop
    try:
        drop = df[df.Event == 'drop'].copy()
        drop.plot(x='Time', y='Sequence Number', kind='scatter', marker='x', s=10, figsize=FIG_SIZE, ax=ax1)
    except TypeError:
        pass
    # ack
    ack = df[df.Event == 'ack'].copy()
    ax = ack.plot(x='Time', y='Sequence Number', kind='scatter', marker='.', s=2, figsize=FIG_SIZE, ax=ax1)
    ax.set_xlim(-0.1, MAX_SEC)
    ax.set_xlabel('Time')
    ax.set_ylabel('Sequence Number')
    plt.suptitle("")
    plt.title(title)
    plt.savefig(outfile, dpi=300)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence_file')
    parser.add_argument('cwnd_file')
    parser.add_argument('out_dir')
    parser.add_argument('-t', '--title', default='')
    args = parser.parse_args()

    out_dir = args.out_dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    cwnd(args.cwnd_file, os.path.join(out_dir, 'cwnd.png'), title=args.title)
    sequence(args.sequence_file, os.path.join(out_dir, 'sequence.png'), title=args.title)

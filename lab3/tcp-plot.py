#!/usr/bin/env python3

import os
import argparse
import matplotlib.pyplot as plt
import pandas as pd

plt.style.use('ggplot')
pd.set_option('display.width', 1000)

SCALE = .75
FIG_SIZE = (11 * SCALE, 5.6 * SCALE)
CWND_FIG_SIZE = (8 * SCALE, 5.6 * SCALE)
MAX_SEC = 6
MSS = 1000
SEQ_MOD = 60

def cwnd(infile, outfile, title=''):
    print('Generating congestion window graph...')
    plt.figure()
    df = pd.read_csv(infile).drop_duplicates('Time')
    df['Effective Congestion Window'] /= MSS
    df['Congestion Window'] /= MSS
    df['Threshold'] /= MSS
    df['Time'] += 1
    ax = df.plot(x='Time', y='Congestion Window', figsize=CWND_FIG_SIZE, c='#348ABD')
    df[(df.shift() != df)['Effective Congestion Window']].plot(
        c='#E24A33', marker='.', linestyle='None', figsize=CWND_FIG_SIZE,
        x='Time', y='Effective Congestion Window', ax=ax, zorder=10
    )
    # set the axes
    ax.set_xlabel('Time')
    ax.set_ylabel('Congestion Window (in MSS)')
    ax.set_xlim(.9, MAX_SEC)
    plt.suptitle("")
    plt.title(title)
    plt.savefig(outfile, bbox_inches='tight')

def sequence(infile, outfile, title=''):
    print('Generating sequence graph...')
    plt.figure()
    df = pd.read_csv(infile, dtype={'Time': float, 'Sequence Number': int})
    df['Time'] += 1
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
        drop.plot(x='Time', y='Sequence Number', kind='scatter', c='r', marker='x', s=10, figsize=FIG_SIZE, ax=ax1)
    except TypeError:
        pass
    # ack
    ack = df[df.Event == 'ack'].copy()
    ax = ack.plot(x='Time', y='Sequence Number', kind='scatter', c='k', marker='.', s=2, figsize=FIG_SIZE, ax=ax1)
    ax.set_xlim(.9, MAX_SEC)
    ax.set_ylim(-1, 60)
    ax.set_xlabel('Time')
    ax.set_ylabel('Sequence Number (in MSS, mod 60)')
    plt.suptitle("")
    plt.title(title)
    plt.savefig(outfile, dpi=300, bbox_inches='tight')


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

#!/usr/bin/python3
"""SGPU

Show GPU allocations of each job queued by Slurm.

Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    January 16, 2020
"""
from subprocess import Popen, PIPE
from datetime import datetime
from os import linesep
from argparse import ArgumentParser
import re


def parse_args():
    p = ArgumentParser(description='shows all jobs in the slurm queue and their'
                                   ' stats, including gpu allocations')

    p.add_argument('-a', '--all', action='store_true',
                   help='runs this command on all dgx servers and shows the'
                        'results.')

    return p.parse_args()


def sgpu(ssh=None):
    """Reads from scontrol and parses the output.

    Args:
        ssh (str or None): If ssh is not None, then runs the scontrol command
             from that address through ssh instead.
    """
    command = []
    if ssh is not None:
        command += ['ssh', '-o', 'StrictHostKeyChecking=no', ssh]
    command += ['scontrol', 'show', 'job']
    # Capture stream from running the scontrol command
    p = Popen(command, stdout=PIPE)
    stdout, stderror = p.communicate()
    results = stdout.decode('UTF-8').split(linesep)

    if len(results) == 1:
        print('')
        return

    pattern = re.compile(r'(\S+)=(\S*)')
    job_dicts = []
    current_job = {}
    for line in results:
        matches = re.findall(pattern, line)
        if len(matches) != 0:
            for k, v in matches:
                current_job[k] = v
        else:
            if len(current_job) != 0:
                job_dicts.append(current_job)
                current_job = {}

    # Extract only the keys that we care about
    parsed_jobs = []
    for job in job_dicts:
        if job['JobState'] == "RUNNING":
            temp = {}
            attributes = [
                'JobId',
                'JobName',
                'UserId',
                'RunTime',
                'StartTime',
                'NumCPUs',
                'MinMemoryNode',
                'WorkDir',
                'Gres'
            ]
            for attribute in attributes:
                temp[attribute] = job[attribute]

            # Parsed the raw dictionary output to more human readable strings
            temp['UserId'] = temp['UserId'].split("(")[0]

            # Change elapsed time to easier to read format
            elapsed_time = temp['RunTime'].split('-')
            if len(elapsed_time) > 1:
                temp['RunTime'] = "{} days {}".format(elapsed_time[0],
                                                      elapsed_time[1])

            # Do the same for the start time
            temp['StartTime'] = datetime.strptime(
                temp['StartTime'], '%Y-%m-%dT%H:%M:%S'
            ).strftime('%d %b - %H:%M:%S')

            # Count GPUs used
            if '(null)' not in temp['Gres']:
                temp['gpu'] = temp['Gres'].split(':')[1]
            else:
                temp['gpu'] = '0'
            del temp['Gres']

            parsed_jobs.append(temp)

    # Now output the values
    header = "{:<5.5} {:<7.7} {:<6.6} {:>18.18}   {:>19.19} {:>5.5} {:>5.5} " \
             "{:>5.5}"
    print('\033[47;30m'
          + header.format('JobId', 'JobName', 'UserId', 'Elapsed Time',
                          'Start Time', 'CPUs', 'Mem', 'GPUs')
          + '\033[49;39m')

    cpu_remaining = 80
    mem_remaining = 508.
    gpu_remaining = 8
    for job in parsed_jobs:
        print(header.format(
            job['JobId'], job['JobName'], job['UserId'], job['RunTime'],
            job['StartTime'], job['NumCPUs'], job['MinMemoryNode'], job['gpu']
        ))

        # Parse CPU
        cpu_remaining -= int(job['NumCPUs'])

        # Parse Memory
        if 'G' in job['MinMemoryNode']:
            mem_remaining -= int(job['MinMemoryNode'].split('G')[0])
        elif 'M' in job['MinMemoryNode']:
            mem_remaining -= int(job['MinMemoryNode'].split('M')[0]) / 1024.

        # Parse GPU
        gpu_remaining -= int(job['gpu'])

    bold = '\033[1m'
    norm = '\033[0m'

    length = '{' + ':>{}'.format(max(len(str(cpu_remaining)),
                                     len(str(mem_remaining)) + 1,
                                     len(str(gpu_remaining))))
    length += '}'

    mem_remaining = str(mem_remaining) + 'G'

    print("\nAvailable resources:\n")
    print('{}CPUs:{}    '.format(bold, norm) + length.format(cpu_remaining))
    print('{}Memory:{}  '.format(bold, norm) + length.format(mem_remaining))
    print('{}GPUs:{}    '.format(bold, norm) + length.format(gpu_remaining))
    print('')


if __name__ == '__main__':
    args = parse_args()
    if args.all:
        print('dgx.cloudlab.zhaw.ch:')
        sgpu('dgx.cloudlab.zhaw.ch')
        print('dgx2.cloudlab.zhaw.ch:')
        sgpu('dgx2.cloudlab.zhaw.ch')
        print('dgx3.cloudlab.zhaw.ch:')
        sgpu('dgx3.cloudlab.zhaw.ch')
    else:
        sgpu()

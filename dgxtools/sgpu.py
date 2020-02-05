"""SGPU

Show GPU allocations of each job queued by Slurm.

Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    January 16, 2020
"""

from subprocess import run
from datetime import datetime


def sgpu():
    # Capture stream from running the scontrol command
    results = run(["scontrol", "show", "job"], capture_output=True, text=True)

    jobs = []
    current_job = []
    # Parse the output into a list of lines
    for line in results.stdout.split("\n"):
        if not line == "":
            current_job.append(line)
        else:
            jobs.append(current_job)
            current_job = []

    # Turn the lists into dictionaries
    raw_job_dicts = []
    for job in jobs:
        job_dict = dict()
        for line in job:
            line = line.split(' ')
            for part in line:
                if part:
                    i = part.split('=')
                    job_dict[i[0]] = i[1]
        if job_dict:
            raw_job_dicts.append(job_dict)

    # Extract only the keys that we care about
    parsed_jobs = []
    for job in raw_job_dicts:
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
    sgpu()

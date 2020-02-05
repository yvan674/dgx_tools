"""GPU.

Tools for getting GPU data. Uses code from the GPUtil, but only the
components we need such that no dependencies are required.

Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    February 05, 2020
"""
from subprocess import Popen, PIPE
import os


def safeFloatCast(str_number):
    try:
        number = float(str_number)
    except:
        number = float('nan')
    return number

def getGPUs():
    # Call the nvidia-smi tool
    try:
        p = Popen(['nvidia-smi',
                   '--query-gpu=index,uuid,utilization.gpu,memory.total,'
                   'memory.used,name',
                   '--format=csv,noheader,nounits'],
                  stdout=PIPE)
        stdout, stderror = p.communicate()
    except:
        return []
    output = stdout.decode('UTF-8')
    output = output.split(os.linesep)

    gpus = []

    for line in output:
        vals = line.split(', ')
        gpu_state = {
            "idx": int(vals[0]),
            "uuid": vals[1],
            "load": safeFloatCast(vals[2]) / 100,
            "memoryTotal": safeFloatCast(vals[3]),
            "memoryUsed": safeFloatCast(vals[4]),
            "name": vals[5]
        }
        gpus.append(GPU(**gpu_state))
    return gpus


class GPU:
    def __init__(self, idx, name, uuid, load, memoryUsed, memoryTotal):
        self.deviceIds = idx
        self.name = name
        self.uuid = uuid
        self.load = load
        self.memoryUsed = memoryUsed,
        self.memoryTotal = memoryTotal

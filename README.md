# DGX Tools
## GPU Graph
Graphically shows GPU usage through the use of line and bar plots on a given machine.

![Screenshot of GPU Graph in use](./screenshot.png)

### Dependencies
The python package [GPUtil](https://pypi.org/project/GPUtil/) is required. 
It can be installed with:

```bash
pip install GPUtil
``` 
### Usage
Run `gpu_graph.py` using python

```bash
python gpu_graph.py
```

The update interval can also be changed by using the `-i` flag.
The update interval is in seconds.
For example,

```bash
python gpu_graph.py -i 0.3  # Set update interval to every 0.3 seconds
```

## Slurm GPU (SGPU)
Details each job in the Slurm queue including their GPU allocations.

The command `squeue` is used to show what jobs are currently in the Slurm queue.
Unfortunately, the job description view shown by it do not include GPU allocations.
This tool provides an easy way to get the GPU usage information in table form as well as showing remaining available resources. 

### Usage
Run `sgpu.py` using python

```bash
python sgpu.py
```

## Attributions
This work uses code from [asciichartpy](https://pypi.org/project/asciichartpy/), licensed under the MIT license.

# fews-bokeh

### Create a bokehfews environment
Use the environment.yml in the repository to create the proper python environment for RESPIGHI in command prompt

```
conda env create -f environment.yml
```

After installation you can activate your environment in command prompt

```
conda activate fewsbokeh
```

### Install fewsbokeh
In the activated environment you will install bokehfews via command prompt in the activated environment:

```
pip install -e .
```

### Launch app
You can launch the bokeh app via de command prompt in the activated environment:

```
path_to_python_installation\envs\fewsbokeh\python.exe -m bokeh serve wik --port 5002
```

Here path_to_python_installation is the directory where python is installed, e.g. c:\Anaconda3

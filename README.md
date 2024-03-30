# 4C-Webviewer

## Purpose

This repo is meant to improve the 4C Webviewer to get it to a stage to make it public to all interested people. It is already subdivided into smaller parts, however it is certainly not optimal yet.

Furthermore, there is no testing included at this stage.

## How to install the conda environment needed for the 4C-Webviewer

This is already rather nice because we only have acceptable dependencies, i.e. open source dependencies:

```
conda create --name <name-of-environment> python=3.10
conda activate <name-of-environment>

pip install lnmmeshio

pip install trame
pip install trame-vuetify trame-vtk
pip install trame-components
pip install --upgrade trame-plotly

pip install plotly
pip install pandas
pip install vtk
```

## How to run the 4C-Webviewer

Change to the directory of the repo. Activate the created conda environment and run

```
python main.py
```

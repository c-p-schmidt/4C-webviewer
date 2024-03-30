# 4C-Webviewer

## Purpose

This repo is meant to improve the 4C Webviewer to get it to a stage to make it public to all interested people. It is already subdivided into smaller parts, however it is certainly not optimal yet.

Furthermore, there is no testing included at this stage.

## How to install the conda environment needed for the 4C-Webviewer

This is already rather nice because we only have acceptable dependencies, i.e. open source dependencies:

```
conda create --name <name-of-environment> python=3.10
conda activate <name-of-environment>
```

## How to install the 4C-webviewer

Go to the source directory and in the activated environment run
```
pip install -e .
```

## How to run the 4C-Webviewer

To start the webviewer, in the conda environment run:
```
fourc_webviewer
```
To directly open a dat file use
```
fourc_webviewer --dat_file <path-to-file>
```

Alternatively change to the directory of the repo. Activate the created conda environment and run
```
python main.py
```

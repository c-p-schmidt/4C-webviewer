import argparse

import fourc_webviewer.run_webserver as webserver


def main():
    arguments = get_arguments()
    webserver.run_webviewer(**arguments)


def get_arguments():
    parser = argparse.ArgumentParser(description="4C Webviewer")
    parser.add_argument("--dat_file", type=str, help="input file path to visualize")

    args = parser.parse_args()

    # return arguments as dict
    return vars(args)

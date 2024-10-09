import lnmmeshio
import numpy as np
import os
import plotly.express as px
import re

from fourc_webviewer.input_file_utils.read_dat_file import (
    add_dat_file_data_to_dis,
    validate_dat_file_path,
)
from pathlib import Path


def convert_to_vtu(dat_file_path, temp_dir):
    # This function converts a given dat file into a corresponding vtu file
    #   Input:
    #       dat_file_path: string: full path to the dat file to be converted
    #   Output:
    #       vtu_file_path: full path of the converted file

    # define the vtu_file_path to have the same name as the dat file, but the its directory is in './temp_files'
    vtu_file_path = str(
        Path(temp_dir) / f"{os.path.splitext(os.path.basename(dat_file_path))[0]}.vtu"
    )

    # validate the provided .dat file path
    validate_dat_file_path(dat_file_path)

    # convert dat file to vtu file and return the path to the vtu file
    try:
        dis = lnmmeshio.read(dat_file_path)
        to_vtu(dis, vtu_file_path)
    except:  # if file conversion not successful
        vtu_file_path = ""
    return vtu_file_path


def function_plot_figure(state_data):
    num_of_time_points = 1000  # number of discrete time points used for plotting
    data = {
        "t": np.linspace(0, state_data.MAX_TIME, num_of_time_points),
        "f(t)": return_function_from_funct_string(
            state_data.FUNCT[1][state_data.SELECTED_FUNCT_INDEX][2][
                state_data.SELECTED_COMP_INDEX
            ]
        )(
            np.full((num_of_time_points,), state_data.X_VAL),
            np.full((num_of_time_points,), state_data.Y_VAL),
            np.full((num_of_time_points,), state_data.Z_VAL),
            np.linspace(0, state_data.MAX_TIME, num_of_time_points),
        ),
    }

    # create figure object with the given data
    fig = px.line(
        data,
        x="t",
        y="f(t)",
        title=f"{state_data.FUNCT[0][state_data.SELECTED_FUNCT_INDEX]}: {state_data.FUNCT[1][state_data.SELECTED_FUNCT_INDEX][0][state_data.SELECTED_COMP_INDEX]}",
    )

    # update layout of the figure
    fig.update_layout(xaxis=dict(tickformat=".2f"), yaxis=dict(tickformat=".2f"))

    return fig


def return_function_from_funct_string(funct_string):
    # The function takes in the value of the funct string coming from a function and returns the parsed function
    #   Input:
    #       funct_string: string of the function, containing the variables t, x, y, z
    #   Output:
    #       return_funct: function of the mentioned arguments

    def funct_using_eval(x, y, z, t):
        # defined functions to be replaced: <def_funct> becomes <np.funct>
        def_funct = ["exp", "sqrt", "log", "sin", "cos", "tan", "heaviside"]

        # funct_string copy
        funct_string_copy = funct_string

        # replace the defined functions in the funct_string with "np.<def_funct>"
        for i in range(len(def_funct)):
            funct_string_copy = funct_string_copy.replace(
                def_funct[i], f"np.{def_funct[i]}"
            )

        # replace pi as well
        funct_string_copy = funct_string_copy.replace("pi", "np.pi")

        # replace the used power sign
        funct_string_copy = funct_string_copy.replace("^", "**")

        # for heaviside: np.heaviside takes two arguments -> second argument denotes the function value at the first argument -> we set it by default to 0
        funct_string_copy = re.sub(
            r"heaviside\((.*?)\)", r"heaviside(\1,0)", funct_string_copy
        )  # usage of raw strings, (.*?) is a non greedy capturing, and \1 replaces the captured value

        return eval(funct_string_copy)  # this parses string in as a function

    return np.frompyfunc(funct_using_eval, 4, 1)


def to_vtu(dis, vtu_file: str, override=True, ascii=False):
    add_dat_file_data_to_dis(dis)

    # write case file
    lnmmeshio.write(
        vtu_file,
        dis,
        file_format="vtu",
        override=override,
    )


def validate_vtu_file_path(vtu_file_path):
    # Validate the file path: file has to exist and end with ".vtu"
    if not vtu_file_path.endswith(".dat"):
        raise Exception("Provided file does not end with .dat!")

    if not os.path.exists(vtu_file_path):
        raise Exception("Provided file does not exist!")

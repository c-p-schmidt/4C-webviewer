# ------------------------------------------------------------------------------#
#                               IMPORT SECTION                                 #
# ------------------------------------------------------------------------------#

import fourc_webviewer.gui_utils as gui
from fourc_webviewer.input_file_utils.dat_file_visualization import (
    convert_to_vtu,
    function_plot_figure,
    return_function_from_funct_string,
)
from fourc_webviewer.input_file_utils.read_dat_file import (
    analyze_functions,
    find_all_linked_materials,
    get_all_material_line_indices_for_clonematmmap_line,
    get_main_and_sub_sections,
    mat_specifiers,
    read_dat_file,
    create_file_object_for_browser
)
from fourc_webviewer.input_file_utils.write_dat_file import write_dat_file
import os
from pathlib import Path
import re
import tempfile
from trame.app import get_server
from vtkmodules.vtkCommonDataModel import vtkDataObject
import fourc_webviewer.vturender as vtu
from fourc_webviewer_default_files import DEFAULT_INPUT_FILE
import time

# ------------------------------------------------------------------------------#
#                              COMMON SERVER SETUP                              #
# ------------------------------------------------------------------------------#

# create server object and the state, control variables
SERVER = get_server()
STATE, CTRL = SERVER.state, SERVER.controller
# STATE contains all the state variables, CTRL contains all the control functions / elements, UI


def run_webviewer(dat_file=None):

    if dat_file is None:
        dat_file = str(DEFAULT_INPUT_FILE)

    # create temporary directory
    temp_dir_object = tempfile.TemporaryDirectory()
    temp_dir = temp_dir_object.name

    STATE.trame__title = "4C Webviewer"  # PAGE TITLE APPEARING IN THE BROWSER TAB
    STATE.RENDER_COUNT = 0  #  Variable used in order to differentiate between state changes at the first, initial rendering

    # ------------------------------------------------------------------------------#
    #                         DEFAULT DAT FILE LOADING                             #
    # ------------------------------------------------------------------------------#

    # global dat and vtu file paths
    default_vtu_path = convert_to_vtu(dat_file, temp_dir)

    # read dat file name
    dat_file_name = os.path.basename(dat_file)

    # read dat file lines
    with open(dat_file, "r") as file:
        dat_file_lines = file.readlines()

    # get dat file size
    dat_file_size = os.path.getsize(dat_file)

    # get last modified time stamp
    dat_file_last_modified = int(os.path.getmtime(dat_file)) 

    # read dat file content
    default_dat_file_content = read_dat_file(dat_file_name, dat_file_lines)

    STATE_initialization(temp_dir, dat_file_name, dat_file_lines, dat_file_size, dat_file_last_modified, default_vtu_path, default_dat_file_content)

    # create reader and update it to read the current vtu file
    reader = vtu.create_vtu_reader()
    vtu.update_vtu_reader(reader, default_vtu_path)

    # create vtu thresholds
    vtu_threshold_mat = vtu.create_vtu_threshold(reader)
    vtu_threshold_condition_points = vtu.create_vtu_threshold_points(reader, STATE)
    vtu_sphere = vtu.create_vtu_sphere(reader)

    STATE.TEMP_DIR = temp_dir
    STATE.READER = reader
    STATE.VTU_THRESHOLD_MAT = vtu_threshold_mat
    STATE.VTU_THRESHOLD_CONDITION_POINTS = vtu_threshold_condition_points
    STATE.VTU_SPHERE = vtu_sphere

    # append functions to CTRL
    CTRL.CLICK_INFO_BUTTON = click_info_button
    CTRL.CLICK_EXPORT_BUTTON = click_export_button
    CTRL.CLICK_CONVERT_BUTTON = click_convert_button
    CTRL.CLICK_SAVE_BUTTON = click_save_button

    # create vtu render window
    render_window = vtu.create_vtu_render_window(
        reader, vtu_threshold_condition_points, vtu_threshold_mat, vtu_sphere
    )

    gui.create_gui(SERVER, render_window)

    # finally start the server after everything is set up
    SERVER.start()

    temp_dir_object.cleanup()  # delete the temporary directory


#   and "real" state changes (value > 0)
def STATE_initialization(temp_dir, dat_file_name, dat_file_lines, dat_file_size, dat_file_last_modified, vtu_path, dat_file_content):
    """Initialize STATE object of the server.

    Args:
        temp_dir (str): temporary directory for the file management.
        dat_file_name (str): name (basename) of the .dat file.
        dat_file_lines (str): list of file lines of the .dat file.
        dat_file_size (int): size of the .dat file.
        dat_file_last_modified (int): timestamp for the last modification of the .dat file.
        vtu_path (str, Path): full path of the converted .vtu file.
        dat_file_content (dict): dictionary containing read-in .dat file information, such as its categories, description, conditions, ...

    Returns:  
        None
    """



    # define and initialize the state variables of the shared state (only these can be used below for v_model, v_show...)

    ### --- STATE VARIABLES FOR PATH INFO --- ###
    STATE.DAT_NAME = dat_file_name  # string: input dat file path
    STATE.DAT_LINES = dat_file_lines # list: file lines of the input dat file
    STATE.DAT_SIZE = dat_file_size # int: size of the .dat file
    STATE.DAT_LAST_MODIFIED = dat_file_last_modified # int: last modified timestamp of the .dat file
    STATE.VTU_PATH = vtu_path  # string: vtu file path
    STATE.EXPORT_DAT_PATH = str(
        Path(temp_dir) / f"new_{os.path.splitext(dat_file_name)[0]}.dat"
    )
    STATE.INPUT_FILE = [create_file_object_for_browser(dat_file_name, dat_file_lines, dat_file_size, dat_file_last_modified)] # list containing a single element, used in the VFileInput object

    ### --- STATE VARIABLES FOR DAT FILE CONTENT --- ###
    STATE.TITLE = dat_file_content["file_title"][0]  # string: .dat file title
    STATE.DESCRIPTION = "\n".join(
        dat_file_content["file_description"]
    )  # list of lines(strings): .dat file description

    STATE.CATEGORIES = dat_file_content[
        "file_categories"
    ]  # 1D-list of strings: read-in categories of the .dat file
    STATE.MAIN_CATEGORIES, STATE.AUX_CATEGORIES = get_main_and_sub_sections(
        [value for value in STATE.CATEGORIES if value != "MATERIALS"]
    )
    # main_categories: list of main categories
    # aux_categories: list of aux categories for each main category (list of lists)
    #    "MATERIALS" excluded
    STATE.CATEGORY_ITEMS = dat_file_content[
        "category_items"
    ]  # list of lists of the form [[<category_item_1_name>, [<category_item_1_val1>, <category_item_1_val2>]], ...]

    # GET THE MATERIALS (used only as a reference for CLONING_MATERIAL_MAP -> source)
    STATE.MATERIALS = STATE.CATEGORY_ITEMS[STATE.CATEGORIES.index("MATERIALS")]

    # FOR EACH MATERIAL: DEFINE THE MODIFIABLE ATTRIBUTES AND THEIR CURRENT VALUES
    STATE.MATERIALS_MODIF_ATTR = []
    # define the parameters to exclude
    mat_attr_to_exclude = mat_specifiers() + [
        "NUMMATEL",
        "NUMFACINEL",
        "NUMPHASE",
        "OCP",
        "Redlich-Kister",
        "X_MIN",
        "X_MAX",
        "OCP_PARA_NUM",
        "OCP_PARA",
        "END",
    ]
    for i in range(len(STATE.MATERIALS[0])):
        # get specific MATERIALS line
        materials_line = STATE.MATERIALS[1][i]

        # get the line attributes: the material type and the material specifiers (references to other materials) are excluded
        materials_line_attributes = [
            attr
            for attr in materials_line.split(" ")[1:]
            if re.search("[A-Z_]+", attr)
            and len([spec for spec in mat_attr_to_exclude if spec in attr]) == 0
        ]

        # get the corresponding values for the attributes
        materials_line_values = []
        for j in range(len(materials_line_attributes)):
            # get index of the current material line attribute in material.split(" ")[1:]
            attr_index = materials_line.split(" ")[1:].index(
                materials_line_attributes[j]
            )

            # get the next index: index of the next parameter value (if available)
            next_index = 0
            try:  # a next parameter value is available
                next_param = [
                    param
                    for param in materials_line.split(" ")[1:][attr_index + 1 :]
                    if re.search("[A-Z_]+", param)
                ][0]
                next_index = materials_line.split(" ")[1:].index(next_param)
            except:  # we have reached the end of the line
                next_index = len(materials_line.split(" ")[1:])

            # append all the line items between the attr_index and the next_index
            materials_line_values.append(
                materials_line.split(" ")[1:][attr_index + 1 : next_index]
            )

        # materials_line_values = [value for (ind,value) in enumerate(materials_line.split(" ")[1:]) if (re.match(reg_exp_for_numbers, value) and materials_line.split(" ")[1:][ind-1] in materials_line_attributes)]

        # append the attributes and values to the corresponding state variable
        STATE.MATERIALS_MODIF_ATTR.append(
            [materials_line_attributes, materials_line_values]
        )

    # GET THE CLONING MATERIAL MAP
    try:  # if the categories contain "CLONING MATERIAL MAP"
        STATE.CLONING_MATERIAL_MAP = STATE.CATEGORY_ITEMS[
            STATE.CATEGORIES.index("CLONING MATERIAL MAP")
        ]
        # transform values in STATE.CLONING_MATERIAL_MAP
        for i in range(len(STATE.CLONING_MATERIAL_MAP[0])):
            # read info of cloning material map line
            (
                src_field,
                src_mat,
                src_mat_line_indices,
                tar_field,
                tar_mat,
                tar_mat_line_indices,
            ) = get_all_material_line_indices_for_clonematmmap_line(
                STATE.CLONING_MATERIAL_MAP[1][i],
                STATE.CATEGORY_ITEMS[STATE.CATEGORIES.index("MATERIALS")],
            )

            # restructure STATE.CLONING_MATERIAL_MAP[0][i]: Should show e.g. "MAT 1 (structure) -> MAT 6 (scatra)"
            STATE.CLONING_MATERIAL_MAP[0][
                i
            ] = f"MAT {src_mat} ({src_field}) -> MAT {tar_mat} ({tar_field})"

            # restructure STATE.CLONING_MATERIAL_MAP[1][i]: Should be a list [["MAT 1 (structure)", "MAT 6 (scatra)"], [<list of line indices in material items linked to MAT 1>, <list of line indices in material items linked to MAT 6>]]
            STATE.CLONING_MATERIAL_MAP[1][i] = [
                [f"MAT {src_mat} ({src_field})", f"MAT {tar_mat} ({tar_field})"],
                [src_mat_line_indices, tar_mat_line_indices],
            ]

        # CLONING MATERIAL MAP is valid(True), as we have read it from the .dat file directly
        STATE.CLONING_MATERIAL_MAP.append(True)
    except:  # else: we only have "MATERIALS" (only one discretized field) -> we will still manage the material info within this state variable (we will only have src materials, no tar materials)

        # append the main category MATERIALS OVERVIEW
        STATE.MAIN_CATEGORIES.append(
            "MATERIALS OVERVIEW"
        )  # add the conditions category manually to the dropdown list
        STATE.AUX_CATEGORIES.append(["MATERIALS OVERVIEW"])

        # initialize empty state variable
        STATE.CLONING_MATERIAL_MAP = [
            [],
            [],
            False,
        ]  # False is appended, as we have not read this from the .dat file, but use the same state variable nonetheless tp structure the materials

        # get all material line indices from "MATERIALS" of the "master" materials, containing references to other materials (see global variable mat_specifiers)
        master_mat_indices = [
            ind
            for (ind, item) in enumerate(STATE.MATERIALS[1])
            if len([spec for spec in mat_specifiers() if spec in item]) > 0
        ]

        # check whether some of the master materials are actually related to others, and eliminate them from the master material index list
        linked_material_indices = (
            []
        )  # list of linked material indices for each of the "master" materials: [<list of linked materials for "MASTER" 1>, <list of linked materials for "MASTER" 2>,... ]
        for i in range(len(master_mat_indices)):
            linked_material_indices.append(
                find_all_linked_materials(
                    STATE.MATERIALS[0][master_mat_indices[i]].replace("MAT ", ""),
                    STATE.CATEGORY_ITEMS[STATE.CATEGORIES.index("MATERIALS")],
                )
            )
        # -> we go through the preliminary master_mat_indices list
        curr_master_ind = 0
        while curr_master_ind < len(master_mat_indices) - 1:
            # check the next items in master_mat_indices
            next_master_ind = curr_master_ind + 1
            while next_master_ind < len(master_mat_indices):
                # the master material with the larger number of linked materials becomes the master, and the other is eliminated from master_mat_indices
                if set(linked_material_indices[next_master_ind]).issubset(
                    set(linked_material_indices[curr_master_ind])
                ):
                    del master_mat_indices[next_master_ind]
                    del linked_material_indices[next_master_ind]
                # next_master_ind stays the same
                elif set(linked_material_indices[curr_master_ind]).issubset(
                    set(linked_material_indices[next_master_ind])
                ):  # this means that the current element is not truly a master -> has to be eliminated and we also break out of the for-loop
                    del master_mat_indices[curr_master_ind]
                    del linked_material_indices[curr_master_ind]
                    break  # curr_ind stays the same
                else:
                    next_master_ind += 1
            else:
                curr_master_ind += 1

        # loop through all master materials
        for i in range(len(master_mat_indices)):
            # append the id of the master material in the first array, e.g. "MAT 1"
            STATE.CLONING_MATERIAL_MAP[0].append(
                STATE.MATERIALS[0][master_mat_indices[i]]
            )

            # get all the related line indices for each master material: (we could theoretically also use linked_material_indices, but this is cleaner)
            list_of_related_material_indices = find_all_linked_materials(
                STATE.MATERIALS[0][master_mat_indices[i]].replace("MAT ", ""),
                STATE.CATEGORY_ITEMS[STATE.CATEGORIES.index("MATERIALS")],
            )

            # append them: STATE.CLONING_MATERIAL_MAP[1][i] should be a list of the form [["MAT 1"],[0,3,4]]
            STATE.CLONING_MATERIAL_MAP[1].append(
                [
                    [STATE.MATERIALS[0][master_mat_indices[i]]],
                    list_of_related_material_indices,
                ]
            )

    # Add the "CONDITIONS" category manually
    STATE.MAIN_CATEGORIES.append(
        "CONDITIONS"
    )  # add the conditions category manually to the dropdown list
    STATE.AUX_CATEGORIES.append(["CONDITIONS"])

    # GET THE FUNCT CATEGORIES
    STATE.FUNCT = [[], []]
    STATE.FUNCT[0] = [
        funct_name
        for funct_name in STATE.CATEGORIES
        if re.search("^FUNCT[0-9]+$", funct_name)
    ]
    STATE.FUNCT[1] = [
        STATE.CATEGORY_ITEMS[STATE.CATEGORIES.index(funct_name)]
        for funct_name in STATE.CATEGORIES
        if re.search("^FUNCT[0-9]+$", funct_name)
    ]
    # transform values in STATE.FUNCT[1]
    parsed_funct = [[] for i in range(len(STATE.FUNCT[1]))]
    for i in range(len(STATE.FUNCT[0])):
        STATE.FUNCT[1][i] = list(analyze_functions(STATE.FUNCT[1][i]))

        # we add now the array of parsed component functions to each function item
        funct_array = []
        for j in range(len(STATE.FUNCT[1][i][0])):
            funct_array.append(
                return_function_from_funct_string(STATE.FUNCT[1][i][2][j])
            )
        parsed_funct[i].append(funct_array)

    # GET THE CONDITION LISTS
    STATE.COND_GENERAL_TYPES = ["DPOINT", "DLINE", "DSURF", "DVOL"]
    STATE.COND_CONTEXT_LIST = dat_file_content["cond_context_list"]
    STATE.COND_ENTITY_LIST = dat_file_content["cond_entity_list"]
    STATE.COND_TYPE_LIST = dat_file_content["cond_type_list"]

    # GET THE RESULT DESCRIPTION
    # STATE.RESULT_DESCRIPTION = STATE.CATEGORY_ITEMS[
    #    STATE.CATEGORIES.index("RESULT DESCRIPTION")
    # ]
    STATE.RESULT_DESCRIPTION = [
        [1, 2, 3, 4, 5, 6, 7, 8],
        [
            "STRUCTURE DIS structure NODE 4 QUANTITY dispy VALUE -1.31962249833408790e-01 TOLERANCE 9.1e-10",
            "STRUCTURE DIS structure NODE 5 QUANTITY dispx VALUE -1.31962249833408513e-01 TOLERANCE 9.1e-10",
            "STRUCTURE DIS structure NODE 8 QUANTITY dispx VALUE -9.06271329067036280e-02 TOLERANCE 9.1e-10",
            "STRUCTURE DIS structure NODE 8 QUANTITY dispy VALUE -9.06271329067068060e-02 TOLERANCE 9.1e-10",
            "STRUCTURE DIS structure NODE 8 QUANTITY dispz VALUE 2.84025416687741394e-01 TOLERANCE 2.8e-09",
            "STRUCTURE DIS structure NODE 6 QUANTITY dispx VALUE -9.06271329067021153e-02 TOLERANCE 9.1e-10",
            "STRUCTURE DIS structure NODE 4 QUANTITY stress_zz VALUE  1.83879098311578976e-01 TOLERANCE 1.8e-07",
            "STRUCTURE DIS structure NODE 8 QUANTITY stress_zz VALUE  1.83879098311589884e-01 TOLERANCE 1.8e-07",
        ],
    ]

    # GET THE GEOMETRY LINES
    STATE.GEOMETRY_LINES = dat_file_content["geometry_lines"]

    ### --- STATE VARIABLES FOR UI SELECTIONS --- ###

    STATE.SELECTED_MAIN_CATEGORY_INDEX = 0  # number: index of the selected category in the toolbar on the left of the GUI
    STATE.SELECTED_MAIN_CATEGORY = STATE.MAIN_CATEGORIES[
        0
    ]  # string: selected category in the toolbar on the left of the GUI
    # INITIALIZE THE SELECTED CLONING MATERIAL MAP LINE
    STATE.SELECTED_CMM_LINE_INDEX = 0
    STATE.SELECTED_CMM_LINE = STATE.CLONING_MATERIAL_MAP[0][
        STATE.SELECTED_CMM_LINE_INDEX
    ]
    # initialize the selected function in the "FUNCTIONS" main category (from the dropdown)
    STATE.SELECTED_FUNCT_INDEX = 0
    # STATE.SELECTED_FUNCT = STATE.FUNCT[0][STATE.SELECTED_FUNCT_INDEX]
    # initialize the selected function component in the "FUNCT<number>" aux categories
    STATE.SELECTED_COMP_INDEX = 0
    STATE.SELECTED_COMP = STATE.FUNCT[1][STATE.SELECTED_COMP_INDEX][0][0]
    # initialize the selected general condition type
    STATE.SELECTED_COND_GENERAL_TYPE_INDEX = 0
    cond_general_type_index = 0
    while cond_general_type_index < len(STATE.COND_GENERAL_TYPES):
        if len(STATE.COND_ENTITY_LIST[cond_general_type_index]) > 0:
            STATE.SELECTED_COND_GENERAL_TYPE_INDEX = cond_general_type_index
            break

        # incrementation
        cond_general_type_index += 1
    STATE.SELECTED_COND_GENERAL_TYPE = STATE.COND_GENERAL_TYPES[
        STATE.SELECTED_COND_GENERAL_TYPE_INDEX
    ]
    # initialize the selected condition entity
    STATE.SELECTED_COND_ENTITY_INDEX = 0
    STATE.SELECTED_COND_ENTITY = STATE.COND_ENTITY_LIST[
        STATE.SELECTED_COND_GENERAL_TYPE_INDEX
    ][STATE.SELECTED_COND_ENTITY_INDEX]

    STATE.SELECTED_RESULT_DESCR_INDEX = 0
    STATE.SELECTED_RESULT_DESCR = STATE.RESULT_DESCRIPTION[1][
        STATE.SELECTED_RESULT_DESCR_INDEX
    ]

    ### --- MISCELLANEOUS STATE VARIABLES --- ###

    # initialize the selected point (x,y,z) for the function visualization
    STATE.X_VAL = 0
    STATE.Y_VAL = 0
    STATE.Z_VAL = 0
    # initialize the t vector for the function visualization
    #   first: we search for the item names "NUMSTEP", "TIMESTEP"
    STATE.NUMSTEP = [
        item[1][item[0].index("NUMSTEP")]
        for item in STATE.CATEGORY_ITEMS
        if "NUMSTEP" in item[0]
    ]
    STATE.TIMESTEP = [
        item[1][item[0].index("TIMESTEP")]
        for item in STATE.CATEGORY_ITEMS
        if "TIMESTEP" in item[0]
    ]
    STATE.MAX_TIME = 0
    if (
        len(STATE.NUMSTEP) > 0 and len(STATE.TIMESTEP) > 0
    ):  # if they are found, we set MAX_TIME accordingly
        STATE.NUMSTEP = STATE.NUMSTEP[0]
        STATE.TIMESTEP = STATE.TIMESTEP[0]
        STATE.MAX_TIME = float(STATE.NUMSTEP) * float(STATE.TIMESTEP)
    else:  # else: arbitrary MAX_TIME
        STATE.MAX_TIME = 100
    # STATE.T_VECT = np.linspace(0,STATE.MAX_TIME,100) -> this doesn't work -> Trame seems to not accepting of numpy arrays as state objects
    # initialize the function value vector for the given point (x,y,z) and the defined time vector
    # STATE.FUNCT_VAL_VECT = return_function_from_funct_string(STATE.FUNCT[1][STATE.SELECTED_FUNCT_INDEX][2][STATE.SELECTED_COMP_INDEX])(np.full((100,), STATE.X_VAL), np.full((100,), STATE.Y_VAL), np.full((100,), STATE.Z_VAL), STATE.T_VECT) -> same here

    # initialize the edit mode toggle value: first on view mode
    STATE.EDIT_MODE_POSSIB = ["VIEW MODE", "EDIT MODE"]
    STATE.EDIT_MODE = STATE.EDIT_MODE_POSSIB[0]

    # initialize info mode value: False (bottom sheet with infos is not displayed until "INFO" button is pressed, and INFO_MODE is then set to True)
    STATE.INFO_MODE = False

    # initialize export mode value: False (bottom sheet with export settings is not displayed until "EXPORT" button is pressed, and EXPORT_MODE is then set to True)
    STATE.EXPORT_MODE = False

    # initialize the export status and its possible choices
    STATE.EXPORT_STATUS_POSSIB = ["INFO", "SUCCESS", "ERROR"] # INFO: button was not yet clicked, SUCCESS: export was successful, ERROR: there was an error after trying to export
    STATE.EXPORT_STATUS = "INFO"

# ------------------------------------------------------------------------------#
#                               STATE CHANGES                                  #
# ------------------------------------------------------------------------------#
 
# after selecting another input .dat file
@STATE.change("INPUT_FILE")
def change_input_file(INPUT_FILE, **kwargs):

    # update file information for the STATE object
    STATE.DAT_NAME = INPUT_FILE[0]["name"]
    STATE.DAT_LINES = INPUT_FILE[0]["content"].decode("utf-8").split("\n")
    STATE.DAT_SIZE = INPUT_FILE[0]["size"]
    STATE.DAT_LAST_MODIFIED = INPUT_FILE[0]["lastModified"]


    if STATE.VTU_PATH != "" and STATE.RENDER_COUNT > 0:
        # trigger deletion of the vtu file from temp_files
        os.remove(STATE.VTU_PATH)

        # CONVERT button becomes visible, while INFO button becomes invisible
        STATE.VTU_PATH = ""

    # set render state to 1 to signify that the first render is done
    STATE.RENDER_COUNT = 1


# after changing the export .dat file path
@STATE.change("EXPORT_DAT_PATH")
def change_export_dat_path(EXPORT_DAT_PATH, **kwargs):
    # set export status to neutral ("INFO")
    STATE.EXPORT_STATUS = STATE.EXPORT_STATUS_POSSIB[0]

# after selecting another main category
@STATE.change("SELECTED_MAIN_CATEGORY")
def change_selected_main_category(SELECTED_MAIN_CATEGORY, **kwargs):
    # get the index of the currently selected category
    index = STATE.MAIN_CATEGORIES.index(SELECTED_MAIN_CATEGORY)

    # update the state variable SELECTED_CATEGORY_INDEX
    STATE.SELECTED_MAIN_CATEGORY_INDEX = index

    # update the selected aux category and its index to 0: reset after selecting another main category
    STATE.SELECTED_AUX_CATEGORY_INDEX = 0
    STATE.SELECTED_AUX_CATEGORY = STATE.AUX_CATEGORIES[
        STATE.SELECTED_MAIN_CATEGORY_INDEX
    ][STATE.SELECTED_AUX_CATEGORY_INDEX]

    # update the content mode
    STATE.CONTENT_MODE = "Nothing"
    if SELECTED_MAIN_CATEGORY in [
        "MATERIALS",
        "RESULT DESCRIPTION",
        "FUNCTIONS",
        "CLONING MATERIAL MAP",
        "MATERIALS OVERVIEW",
        "CONDITIONS",
    ]:  # individual display layout elements for the specified categories
        STATE.CONTENT_MODE = STATE.SELECTED_MAIN_CATEGORY
    else:  # all others are displayed in the same way, specified by the string "PROP_VALUE"
        STATE.CONTENT_MODE = "PROP_VALUE"


# after selecting another aux category
@STATE.change("SELECTED_AUX_CATEGORY")
def change_selected_aux_category(SELECTED_AUX_CATEGORY, **kwargs):
    # update the index
    STATE.SELECTED_AUX_CATEGORY_INDEX = STATE.AUX_CATEGORIES[
        STATE.SELECTED_MAIN_CATEGORY_INDEX
    ].index(SELECTED_AUX_CATEGORY)

    # update selected function index only if the main category is "FUNCTIONS"
    if STATE.SELECTED_MAIN_CATEGORY == "FUNCTIONS":
        STATE.SELECTED_FUNCT_INDEX = STATE.SELECTED_AUX_CATEGORY_INDEX

        # change the component index and the component as well -> reset to the first one
        STATE.SELECTED_COMP_INDEX = 0
        STATE.SELECTED_COMP = STATE.FUNCT[1][STATE.SELECTED_FUNCT_INDEX][0][
            STATE.SELECTED_COMP_INDEX
        ]

        # update the displayed function plot
        CTRL.figure_update(function_plot_figure(STATE))


# after selecting another CMM Line
@STATE.change("SELECTED_CMM_LINE")
def change_selected_cmm_line(SELECTED_CMM_LINE, **kwargs):
    # update the state variable SELECTED_CATEGORY_INDEX
    STATE.SELECTED_CMM_LINE_INDEX = STATE.CLONING_MATERIAL_MAP[0].index(
        SELECTED_CMM_LINE
    )

    # set threshold of the material of the vtk local view
    STATE.VTU_THRESHOLD_MAT.SetLowerThreshold(STATE.SELECTED_CMM_LINE_INDEX + 1)
    STATE.VTU_THRESHOLD_MAT.SetUpperThreshold(STATE.SELECTED_CMM_LINE_INDEX + 1)
    # update the vtk local view
    CTRL.VIEW_UPDATE()


# after selecting another function component
@STATE.change("SELECTED_COMP")
def change_selected_comp(SELECTED_COMP, **kwargs):
    # update the index
    STATE.SELECTED_COMP_INDEX = STATE.FUNCT[1][STATE.SELECTED_FUNCT_INDEX][0].index(
        SELECTED_COMP
    )

    # update the displayed function plot
    CTRL.figure_update(function_plot_figure(STATE))


# after changing the function state
@STATE.change("FUNCT")
def change_funct(FUNCT, **kwargs):
    # update the displayed function plot
    CTRL.figure_update(function_plot_figure(STATE))


# after selecting another general condition type
@STATE.change("SELECTED_COND_GENERAL_TYPE")
def change_selected_cond_general_type(SELECTED_COND_GENERAL_TYPE, **kwargs):
    # update the index
    STATE.SELECTED_COND_GENERAL_TYPE_INDEX = STATE.COND_GENERAL_TYPES.index(
        SELECTED_COND_GENERAL_TYPE
    )

    # reset the cond entity to index 0 and update the vtk figure
    # (if there is a respective cond entity)
    try:
        STATE.SELECTED_COND_ENTITY_INDEX = 0
        STATE.SELECTED_COND_ENTITY = STATE.COND_ENTITY_LIST[
            STATE.SELECTED_COND_GENERAL_TYPE_INDEX
        ][0]
        # set thresholdPoints of the condition of the vtk figure
        STATE.VTU_THRESHOLD_CONDITION_POINTS.SetInputArrayToProcess(
            0,
            0,
            0,
            vtkDataObject.FIELD_ASSOCIATION_POINTS,
            f"{STATE.SELECTED_COND_GENERAL_TYPE.lower()}{STATE.SELECTED_COND_ENTITY_INDEX+1}",
        )
        # update the vtk figure
        CTRL.VIEW_UPDATE()
    except:
        ...


# after selecting another condition entity
@STATE.change("SELECTED_COND_ENTITY")
def change_selected_cond_entity(SELECTED_COND_ENTITY, **kwargs):
    # update the index
    STATE.SELECTED_COND_ENTITY_INDEX = STATE.COND_ENTITY_LIST[
        STATE.SELECTED_COND_GENERAL_TYPE_INDEX
    ].index(SELECTED_COND_ENTITY)

    # set thresholdPoints of the condition of the vtk figure
    STATE.VTU_THRESHOLD_CONDITION_POINTS.SetInputArrayToProcess(
        0,
        0,
        0,
        vtkDataObject.FIELD_ASSOCIATION_POINTS,
        f"{STATE.SELECTED_COND_GENERAL_TYPE.lower()}{SELECTED_COND_ENTITY}",
    )
    # update the vtk figure
    CTRL.VIEW_UPDATE()


# after selecting a result description from the list: index change
@STATE.change("SELECTED_RESULT_DESCR_INDEX")
def change_selected_result_descr_index(SELECTED_RESULT_DESCR_INDEX, **kwargs):
    # get corresponding selected result description
    STATE.SELECTED_RESULT_DESCR = STATE.RESULT_DESCRIPTION[1][
        SELECTED_RESULT_DESCR_INDEX
    ]


# after selecting a result description from the list: item change
@STATE.change("SELECTED_RESULT_DESCR")
def change_selected_result_descr(SELECTED_RESULT_DESCR, **kwargs):
    # check if the line contains the marker "NODE"
    if len(re.findall("NODE", STATE.SELECTED_RESULT_DESCR)) > 0:
        # get the specified node
        result_descr_components = STATE.SELECTED_RESULT_DESCR.split(" ")
        node_index = (
            int(result_descr_components[result_descr_components.index("NODE") + 1]) - 1
        )

        # update graphic representation
        node_coords = STATE.READER.GetOutput().GetPoints().GetPoint(node_index)
        STATE.VTU_SPHERE.SetCenter(node_coords[0], node_coords[1], node_coords[2])
        # update the vtk figure
        CTRL.VIEW_UPDATE()


# changing the values for t_max, x, y or z for the function plots
@STATE.change("MAX_TIME", "X_VAL", "Y_VAL", "Z_VAL")
def change_t_max_xyz(MAX_TIME, X_VAL, Y_VAL, Z_VAL, **kwargs):
    # update the displayed function plot
    CTRL.figure_update(function_plot_figure(STATE))


# modifying the value in MATERIALS_MODIF_ATTR (EDIT MODE)
@STATE.change("MATERIALS_MODIF_ATTR")
def change_materials_modif_attr(MATERIALS_MODIF_ATTR, **kwargs):
    # rebuild STATE.MATERIALS with the info of STATE.MATERIALS_MODIF_ATTR
    for mat_ind in range(len(STATE.MATERIALS[0])):
        # get material line components
        material_line_components = STATE.MATERIALS[1][mat_ind].split(" ")
        for attr_index in range(len(STATE.MATERIALS_MODIF_ATTR[mat_ind][0])):
            # get the start and end indices of the values for the considered attribute in material_line_components
            start_value_index = (
                material_line_components.index(
                    STATE.MATERIALS_MODIF_ATTR[mat_ind][0][attr_index]
                )
                + 1
            )
            end_value_index = start_value_index + len(
                STATE.MATERIALS_MODIF_ATTR[mat_ind][1][attr_index]
            )  # taking into account multiple components for the attribute

            # replace the material line components within start and end indices with the corresponding values
            material_line_components[start_value_index:end_value_index] = (
                STATE.MATERIALS_MODIF_ATTR[mat_ind][1][attr_index]
            )

        # rebuild the material line
        STATE.MATERIALS[1][mat_ind] = " ".join(material_line_components)

    # push the server change of STATE.MATERIALS to the client
    STATE.dirty("MATERIALS")


# after modifying the export mode (either after clicking on EXPORT or after canceling the export bottom sheet)
@STATE.change("EXPORT_MODE")
def change_export_mode(EXPORT_MODE, **kwargs):
    STATE.EXPORT_STATUS = STATE.EXPORT_STATUS_POSSIB[0] # set export status to neutral ("INFO")


# ------------------------------------------------------------------------------#
#                            CLICK EVENT FUNCTIONS                             #
# ------------------------------------------------------------------------------#
# modify STATE.INFO_MODE if the <INFO> button is clicked
def click_info_button():
    STATE.INFO_MODE = not STATE.INFO_MODE


# modify STATE.EXPORT_MODE if the <EXPORT> button is clicked
def click_export_button():
    STATE.EXPORT_MODE = not STATE.EXPORT_MODE

# convert provided dat file
def click_convert_button():
    # create temporary .dat file from its name and content
    temp_dat_file = os.path.join(STATE.TEMP_DIR, STATE.DAT_NAME)
    with open(temp_dat_file, "w") as f:
            f.write("\n".join(STATE.DAT_LINES))

    # global dat and vtu file paths
    vtu_path = convert_to_vtu(temp_dat_file, STATE.TEMP_DIR)

    # update reader to read the current vtu file
    vtu.update_vtu_reader(STATE.READER, vtu_path)

    # read dat file content
    dat_file_content = read_dat_file(STATE.DAT_NAME, STATE.DAT_LINES)

    # save render count and temporarily set the corresponding state variable to 0,
    # in order to avoid the deletion of the vtu file due to changes in STATE.INPUT_FILE
    render_count = STATE.RENDER_COUNT
    STATE.RENDER_COUNT = 0

    # reinitialize all state variables
    STATE_initialization(STATE.TEMP_DIR, STATE.DAT_NAME, STATE.DAT_LINES, STATE.DAT_SIZE, STATE.DAT_LAST_MODIFIED, vtu_path, dat_file_content)

    # flush state: force push server changes
    STATE.flush()

    # it is not required to update the actor_cond point size
    STATE.VTU_SPHERE.SetRadius(
        vtu.get_length_scale_rendered_object(STATE.READER) / 50.0
    )

    CTRL.VIEW_RESET_CAMERA()
    CTRL.VIEW_UPDATE()

    # reestablish the render count
    STATE.RENDER_COUNT = render_count




# export dat file
def click_save_button():
    try:
        write_dat_file(
            STATE.TITLE,
            STATE.DESCRIPTION,
            STATE.CATEGORIES,
            STATE.CATEGORY_ITEMS,
            STATE.MATERIALS,
            STATE.CLONING_MATERIAL_MAP,
            STATE.FUNCT,
            STATE.COND_GENERAL_TYPES,
            STATE.COND_ENTITY_LIST,
            STATE.COND_CONTEXT_LIST,
            STATE.COND_TYPE_LIST,
            STATE.RESULT_DESCRIPTION,
            STATE.GEOMETRY_LINES,
            STATE.EXPORT_DAT_PATH,
        )
        STATE.EXPORT_STATUS = STATE.EXPORT_STATUS_POSSIB[1]
    except:
        STATE.EXPORT_STATUS = STATE.EXPORT_STATUS_POSSIB[2]

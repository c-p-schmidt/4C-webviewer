"""Dat file writer utils."""

import math
import re


def write_dat_file(
    title,
    description,
    categories,
    category_items,
    materials,
    cloning_material_map,
    funct,
    cond_general_types,
    cond_entity_list,
    cond_context_list,
    cond_type_list,
    result_description,
    geometry_lines,
    dat_file_path,
):
    # This function writes a dat file from given input info
    #   Input:
    #       title: string: title of the file; Example -> "Simulation of something"
    #       description: string: description of the file; Example -> "This is a generic description \n Here you could write other things as well"
    #       categories: list of strings: categories of the dat file; Example -> ["PROBLEM SIZE","PROBLEM TYP",...]
    #       category_items: [name, value] pairs for each category; Example -> [["DIM","3"], ["LINEAR_SOLVER","1"],...]
    #                        NOTE: the categories MATERIALS, CLONING_MATERIAL_MAP, FUNCT and the conditions are handled separately. Therefore, their [name, value] pairs here are irrelevant
    #       materials: [<list of material names>,<list of material info>]; Example -> [["MAT 1", "MAT 2",...],["MAT_MultiplicativeSplitDefgradElastHyper NUMMATEL 1 MATIDSEL 4 NUMFACINEL 1 INELDEFGRADFACIDS 5 DENS 1.0",...]]
    #       cloning_material_map: [<list of material dependencies>, [...], [<True or False>]]; Example: [['MAT 1 (structure) -> MAT 6 (scatra)', 'MAT 2 (structure) -> MAT 7 (scatra)', 'MAT 3 (structure) -> MAT 8 (scatra)',... ],[...],[True]] -> True: means that we read CLONING MATERIAL MAP from the original .dat file and have to therefore write it to the export file as well; if False: it means we didn't read it from the .dat file but only used the same variable name for convenience -> should not be included in the .dat file
    #       funct: [<list of funct names>, <list of funct specifications>] for the functions; Example: [["FUNCT1", "FUNCT2",...], [[["COMPONENT 0", "COMPONENT 1", "COMPONENT 2"],["SYMBOLIC_FUNCTION_OF_SPACE_TIME","SYMBOLIC_FUNCTION_OF_SPACE_TIME","SYMBOLIC_FUNCTION_OF_SPACE_TIME"],["10.88*t","sin(x)*cos(t)","180.0"]],...]
    #       cond_general_types: list of general types of conditions, by default ["DPOINT","DLINE","DSURF","DVOL"]
    #       cond_entity_list: [[<list of condition entities for DPOINT conditions>],[<list of condition entities for DLINE conditions>],[<list of condition entities for DSURF conditions>],[<list of condition entities for DVOL conditions>]]; Example: [[1,2],[1,2,3],[1],[1,2,3,4]]
    #       cond_context_list: [[<list of condition contexts for DPOINT conditions>],[<list of condition contexts for DLINE conditions>],[<list of condition contexts for DSURF conditions>],[<list of condition contexts for DVOL conditions>]]; Example: [["NUMDOF 3 ONOFF 1 1 1 VAL 0.0 0.0 0.0 FUNCT none none none","NUMDOF 3 ONOFF 1 1 1 VAL 0.0 0.0 0.0 FUNCT none none none"],[...],[["1 Slave S2I_KINETICS_ID  1", "1 Slave KINETIC_MODEL Butler-Volmer NUMSCAL 1 STOICHIOMETRIES -1  E- 1  K_R  2.07e-5 ALPHA_A 0.5 ALPHA_C 0.5 IS_PSEUDO_CONTACT 0"],[...],...],[...]]
    #       cond_type_list: [[<list of condition types for DPOINT conditions>],[<list of condition types for DLINE conditions>],[<list of condition types for DSURF conditions>],[<list of condition types for DVOL conditions>]]; Example: [["DESIGN POINT DIRICH CONDITIONS","DESIGN POINT DIRICH CONDITIONS"],[...],[["DESIGN CCCV CELL CYCLING SURF CONDITIONS", "DESIGN CCCV HALF-CYCLE SURF CONDITIONS"],[...],...],[...]]
    #       result_description: [[<list of result line indices>], [<list of result line descriptions>]]; Example: [[1,2,3,...],["SCATRA DIS scatra NODE 10 QUANTITY phi1 VALUE  1.08434445258624166e+01 TOLERANCE 1.1e-07", "SCATRA DIS scatra SPECIAL QUANTITY soc1 VALUE  9.98966931042610251e-01 TOLERANCE 1.0e-08",...]]
    #       geometry_lines: [<lines with geometry specific info>]; Example: ["-----------------------------------------------DNODE-NODE TOPOLOGY", "NODE    36 DNODE 1", "NODE    163 DNODE 1", ..., "-----------------------------------------------DLINE-NODE TOPOLOGY", "NODE    36 DLINE 1", "NODE    105 DLINE 1",...]

    # initialize lines_list, containing all the file lines
    lines_list = ["//", "//"]

    # number of characters for "===" and "---" lines
    num_of_chars = 100

    # line length for the category lines with <name     value>
    line_length = 60

    # append title section
    lines_list.append("=" * num_of_chars)
    lines_list.append(
        " " * math.floor((num_of_chars - len(title)) / 2)
        + title
        + " " * math.ceil((num_of_chars - len(title)) / 2)
    )
    lines_list.append("=" * num_of_chars)

    # append description section
    lines_list.append("-" * (num_of_chars - len("TITLE")) + "TITLE")
    lines_list.extend(description.split("\n"))

    # loop through all categories and append their <name     value> sections
    for cat_ind, cat in enumerate(categories):
        if (
            cat not in ["MATERIALS", "CLONING MATERIAL MAP", "RESULT DESCRIPTION"]
            and "FUNCT" not in cat
        ):
            lines_list.append("-" * (num_of_chars - len(cat)) + cat)

            # get the category items
            category_names = category_items[cat_ind][0]
            category_values = category_items[cat_ind][1]

            for i in range(len(category_names)):
                lines_list.append(
                    category_names[i]
                    + (
                        " "
                        * (
                            line_length
                            - len(category_names[i])
                            - len(category_values[i])
                        )
                    )
                    + category_values[i]
                )

    # category "MATERIALS": loop through all materials and insert the material "name" and "value"
    lines_list.append("-" * (num_of_chars - len("MATERIALS")) + "MATERIALS")
    for mat_ind in range(len(materials[0])):
        lines_list.append(materials[0][mat_ind] + " " + materials[1][mat_ind])

    # category "CLONING MATERIAL MAP": loop through all items, and identify the src and tar materials and fields
    if cloning_material_map[-1]:
        lines_list.append(
            "-" * (num_of_chars - len("CLONING MATERIAL MAP")) + "CLONING MATERIAL MAP"
        )
        for cmm_item in cloning_material_map[0]:
            # find source and target material
            src_mat = re.findall("MAT [0-9]+", cmm_item)[0].replace("MAT ", "")
            tar_mat = re.findall("MAT [0-9]+", cmm_item)[1].replace("MAT ", "")

            # find src and tar field
            src_field = re.findall(r"\((.*?)\)", cmm_item)[0]
            tar_field = re.findall(r"\((.*?)\)", cmm_item)[1]

            # put the infos together in a cmm line
            lines_list.append(
                f"SRC_FIELD {src_field} SRC_MAT {src_mat} TAR_FIELD {tar_field} TAR_MAT {tar_mat}"
            )

    """
    # categories "FUNCT [0-9]": loop through all functions and their components
    for funct_ind in range(len(funct[0])):
        # get function name and append it as a category name
        funct_name = funct[0][funct_ind]
        lines_list.append("-"*(num_of_chars - len(funct_name)) + funct_name)

        # append function specific lines
        for comp_ind in range(len(funct[1][funct_ind][0])):
            # get component name
            comp_name = funct[1][funct_ind][0][comp_ind]

            # get component function type
            comp_funct_type = funct[1][funct_ind][1][comp_ind]

            # get function string
            comp_funct_string = funct[1][funct_ind][2][comp_ind]

            # append informations to a component specific line
            lines_list.append(f"{comp_name} {comp_funct_type} {comp_funct_string}")
    """

    # append the functions
    for funct_ind in range(len(funct[0])):
        # function name
        lines_list.append(
            "-" * (num_of_chars - len(funct[0][funct_ind])) + funct[0][funct_ind]
        )
        # component by component
        for comp_ind in range(len(funct[1][i][0])):
            lines_list.append(
                f"{funct[1][funct_ind][0][comp_ind]} {funct[1][funct_ind][1][comp_ind]} {funct[1][funct_ind][2][comp_ind]}"
            )

    # category "RESULT DESCRIPTION": append them line by line
    lines_list.append(
        "-" * (num_of_chars - len("RESULT DESCRIPTION")) + "RESULT DESCRIPTION"
    )
    for res_descr_line in result_description[1]:
        lines_list.append(res_descr_line)

    # conditions section
    #   we loop through all the general types ["DPOINT","DLINE","DSURF","DVOL"]
    for gen_type_ind in range(len(cond_general_types)):
        # get the specific lists of entities, contexts and types
        curr_entity_list = cond_entity_list[gen_type_ind].copy()
        curr_context_list = cond_context_list[gen_type_ind].copy()
        curr_type_list = cond_type_list[gen_type_ind].copy()

        # get all types of conditions available
        all_types_available = list(
            set(flatten_input_list(curr_type_list))
        )  # remove non-unique values by transforming it first to a set and then back to a list

        # now loop through all of the available types and find corresponding entities and contexts
        for type_ind, type_item in enumerate(all_types_available):
            # append lines for the considered type item
            lines_list.append("-" * (num_of_chars - len(type_item)) + type_item)
            lines_list.append(
                f"{cond_general_types[gen_type_ind]} 0"
            )  # preliminary number of condition: 0 -> is modified down below

            # we consider each entity separately
            line_counter = 0
            for entity_ind in range(len(curr_entity_list)):
                # now we go through all conditions of the considered entity
                if isinstance(curr_type_list[entity_ind], list):
                    for type_ind_of_entity in range(len(curr_type_list[entity_ind])):
                        # if the type of the current entity is the same as type_item, append the specific condition line
                        if curr_type_list[entity_ind][type_ind_of_entity] == type_item:
                            lines_list.append(
                                f"E {entity_ind + 1} - {curr_context_list[entity_ind][type_ind_of_entity]}"
                            )
                            line_counter += 1
                else:
                    # check whether the type of the entity condition corresponds to the considered type_item
                    if curr_type_list[entity_ind] == type_item:
                        lines_list.append(
                            f"E {entity_ind} - {cond_context_list[entity_ind][type_ind_of_entity]}"
                        )
                        line_counter += 1
            # modify the preliminary number of conditions based on the line_counter
            lines_list[-line_counter - 1] = (
                f"{cond_general_types[gen_type_ind]} {line_counter}"
            )

    # finally, append the geometry lines corresponding to geometric info
    lines_list.extend(geometry_lines)

    f = open(dat_file_path, "w")
    f.write("\n".join(lines_list))


def flatten_input_list(lst):
    # This function returns all the elements available in a list recursively
    #   E.g. for ["Element 1", ["Subelement 1","Subelement 2"]] the function returns ["Element 1", "Subelement 1", "Subelement 2"]
    flattened_list = []
    for item in lst:
        if isinstance(item, list):
            flattened_list.extend(flatten_input_list(item))
        else:
            flattened_list.append(item)
    return flattened_list

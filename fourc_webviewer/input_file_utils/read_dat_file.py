# ------------------------------------------------------------------------------#
#                     READ AND SECTION A PROVIDED DAT FILE                     #
# ------------------------------------------------------------------------------#
import os
import re

from fourc_webviewer.python_utils import list_is_iterable


def add_dat_file_data_to_dis(dis):
    dis.compute_ids(zero_based=False)

    # write node data
    for n in dis.nodes:
        # write node id
        n.data["node-id"] = n.id
        n.data["node-coords"] = n.coords

        # write fibers
        for name, f in n.fibers.items():
            n.data["node-" + name] = f.fiber

        # write dpoints
        for dp in n.pointnodesets:
            n.data["dpoint{0}".format(dp.id)] = 1.0

        # write dlines
        for dl in n.linenodesets:
            n.data["dline{0}".format(dl.id)] = 1.0

        # write dsurfs
        for ds in n.surfacenodesets:
            n.data["dsurf{0}".format(ds.id)] = 1.0

        # write dvols
        for dv in n.volumenodesets:
            n.data["dvol{0}".format(dv.id)] = 1.0

    # write element data
    for eles in dis.elements.values():
        for ele in eles:
            ele.data["element-id"] = ele.id

            # write mat
            if "MAT" in ele.options:
                if list_is_iterable(ele.options["MAT"]):
                    ele.data["element-material"] = int(ele.options["MAT"][0])
                else:
                    ele.data["element-material"] = int(ele.options["MAT"])

            # write fibers
            for name, f in ele.fibers.items():
                ele.data["element-" + name] = f.fiber


def analyze_functions(function_item):
    # This function analyzes a given function item and returns vectors of the
    # function types, component names and their respective strings in each dimension
    #   Input:
    #       function_item in the form [[1,2],['COMPONENT 0 ...','COMPONENT 1 ...']]
    #   Output:
    #       funct_comp_names in the form [COMPONENT 0,1]
    #       funct_types in the form ["SYMBOLIC_FUNCTION_OF_SPACE_TIME", "SYMBOLIC_FUNCTION_OF_SPACE_TIME"]
    #       funct_strings in the form ["10.0*t*(x+y)", "310.0/x"]

    k = 0
    funct_comp_names = []
    funct_types = []
    funct_strings = []

    while k < len(
        function_item[0]
    ):  # read through the provided lines for the FUNCT item
        if (re.search("^COMPONENT [0-9]", function_item[1][k])) or (
            re.search("^SYMBOLIC[_A-Z]+ [\S]+$", function_item[1][k])
            and len(function_item[0]) == 1
        ):  # implementation for single functions -> either they start with "COMPONENT " or with "SYMBOLIC_..."(in this case, they have to be one-dimensional)
            funct_types.append(re.findall("SYMBOLIC[_A-Z]+", function_item[1][k])[0])
            funct_strings.append(
                re.findall("[\S]+$$", function_item[1][k])[0]
            )  # at the end of the line and containing only numbers and t,x,y,z

            if re.search(
                "^COMPONENT [0-9]", function_item[1][k]
            ):  # if there is a component item
                funct_comp_names.append(
                    re.findall("^COMPONENT [0-9]", function_item[1][k])[0]
                )
            else:
                funct_comp_names.append("COMPONENT 0")

            # increment k
            k += 1

        else:
            raise Exception(
                f"The function analysis for the line {function_item[1][k]} not implemented yet!"
            )

    return funct_comp_names, funct_types, funct_strings


def find_all_linked_materials(material_number, material_items):
    # RECURSIVE FUNCTION
    # The function takes in a material number, and finds all linked materials to this material.
    #   Input:
    #       material number -> e.g. 1 for "MAT 1"
    #       material_items -> e.g. [['MAT 1','MAT 2',...],
    #                               [['MAT_MultiplicativeSp...ElastHyper', 'NUMMATEL', '1', 'MATIDSEL', '4', 'NUMFACINEL', '1', 'INELDEFGRADFACIDS', '5', 'DENS', '1.0', '2'],[...]...]]
    #   Output:
    #       list_of_line_indices_in_material_items: list of ints: containing the line indices in material_items corresponding to the found linked materials

    # find the line in material_items corresponding to the material index
    material_line_index = material_items[0].index(
        f"MAT {material_number}"
    )  # index of line in material_items corresponding to the considered material with material_number
    material_line = material_items[1][material_line_index]
    list_of_line_indices_in_material_items = [material_line_index]

    # divide the material_index line into its components split by " "
    material_line_components = material_line.split(" ")

    # search for the specifiers within the material_index line in material_items
    # material_mat_specifiers = [item for item in mat_specifiers if re.search(f"{item} ", material_line)]
    material_mat_specifiers = [
        spec_item
        for spec_item in mat_specifiers()
        if spec_item in material_line_components
    ]

    if len(material_mat_specifiers) == 0:  # no further linked materials
        return list_of_line_indices_in_material_items
    else:  # there are further linked materials

        # for each of the found specifiers: find the values (equivalent to material indices of the linked materials)
        for spec in material_mat_specifiers:
            # find the index of the spec in the material_index_line_components
            spec_index = material_line_components.index(spec)

            # find the index of the next purely alphabetical component in material_index_line_components
            next_index = spec_index + 1
            while next_index < len(material_line_components):
                # check for alphabetical component
                if re.search("^[A-Za-z]+", material_line_components[next_index]):
                    break

                # increment next_index
                next_index += 1

            # add the line indices of the found materials (and their linked materials) to list_of_lines_in_material_items
            for index in range(spec_index + 1, next_index):
                list_of_line_indices_in_material_items += find_all_linked_materials(
                    material_line_components[index], material_items
                )
        return list_of_line_indices_in_material_items


def get_all_material_line_indices_for_clonematmmap_line(cmm_line, material_items):
    # For a CLONING MATERIAL MAP line, the function determines all the lines of the materials associated with this line (by using the line elements of material_items).
    #   Input:
    #       cmm_line -> e.g. 'SRC_FIELD structure SRC_MAT 3 TAR_FIELD scatra TAR_MAT 8'
    #       material_items -> e.g. [['MAT 1','MAT 2',...],
    #                                   [['MAT_MultiplicativeSp...ElastHyper', 'NUMMATEL', '1', 'MATIDSEL', '4', 'NUMFACINEL', '1', 'INELDEFGRADFACIDS', '5', 'DENS', '1.0', '2'],[...]...]]
    #   Output:
    #          src_field: source field
    #          src_mat: the index of the source material
    #          src_mat_line_indices: all the line indices in material_items associated with the src_material
    #                              (including the linked materials, e.g. elastic components)
    #          tar_field, tar_mat and tar_mat_lines -> analogous for the target material

    # analyze the provided cmm_line for src_field, src_mat, tar_field, tar_mat
    cmm_line_components = cmm_line.split(" ")
    src_field = cmm_line_components[cmm_line_components.index("SRC_FIELD") + 1]
    src_mat = cmm_line_components[cmm_line_components.index("SRC_MAT") + 1]
    tar_field = cmm_line_components[cmm_line_components.index("TAR_FIELD") + 1]
    tar_mat = cmm_line_components[cmm_line_components.index("TAR_MAT") + 1]

    # now find the lines in material_items for the src_mat (and tar_mat) and its respective linked materials (fully recursive -> all linked materials are found, not only the direct children)
    src_mat_line_indices = find_all_linked_materials(src_mat, material_items)
    tar_mat_lines_indices = find_all_linked_materials(tar_mat, material_items)

    return (
        src_field,
        src_mat,
        src_mat_line_indices,
        tar_field,
        tar_mat,
        tar_mat_lines_indices,
    )


""""returns all specifiers for references to other materials (regarding IDs)"""


def get_main_and_sub_sections(sections_list):
    # For given .dat file sections, this function determines all the main sections.
    #   e.g. SCALAR TRANSPORT DYNAMIC / SCALAR TRANSPORT DYNAMIC/STABILIZATION,
    #        SCALAR TRANSPORT DYNAMIC/S2I COUPLING
    #   are all sub sections contained within the same main section SCALAR TRANSPORT DYNAMIC
    #   Input:
    #       sections_list: list of all sections read from the .dat file
    #   Output::
    #       main_sections: list of the main sections [<main_1>, <main_2>, ....]
    #       sub_sections: list of the sub sections for each main category [[<aux_1_1>, <aux_1_2>,...], [<aux_2_1>, <aux_2_2>,...],...]

    # create a copy of sections_list
    sections = sections_list.copy()

    # create arrays to be returned
    main_sections = []
    sub_sections = []

    # loop through the sections (.dat file sections)
    while len(sections) > 0:
        # check if the section at the current index is "FUNCT<number>"
        if re.match("^FUNCT[0-9]+", sections[0]):  # yes
            # append the main section "FUNCTIONS"
            main_sections.append("FUNCTIONS")

            sub_sections_to_be_added = []  # list of sub sections to be added
            # add current element to sub sections and remove it from sections
            sub_sections_to_be_added.append(sections.pop(0))

            # go through the other elements and remove them
            j = 0
            while j < len(sections):
                if re.match("^FUNCT[0-9]+", sections[j]):
                    sub_sections_to_be_added.append(sections.pop(j))
                else:
                    # increment j
                    j += 1

            # add the sub sections
            sub_sections.append(sub_sections_to_be_added)

        else:  # no
            # check if element already in main sections -> SHOULD NEVER HAPPEN
            if sections[0].split("/")[0] in main_sections:
                raise Exception(
                    f"The item {sections[0]} is already in {main_sections}! There is a problem in the code!"
                )
            else:
                # get main category name to be added
                main_section_name = sections[0].split("/")[0]

                # add the main category
                main_sections.append(main_section_name)

                # add the current element to the list of aux elements to be added
                sub_sections_to_be_added = []
                sub_sections_to_be_added.append(sections.pop(0))

                # go through the other elements and remove them
                j = 0
                while j < len(sections):
                    if sections[j].split("/")[0] == main_section_name:
                        sub_sections_to_be_added.append(sections.pop(j))
                    else:
                        # increment j
                        j += 1

                # add the sub sections
                sub_sections.append(sub_sections_to_be_added)

    return main_sections, sub_sections


def mat_specifiers():
    return [
        "MATIDSEL",
        "INELDEFGRADFACIDS",
        "PHASEIDS",
        "MATIDS",
        "MATID",
        "VP_FR_MATID",
    ]


def read_dat_file(dat_file_path):
    # This function reads in the content of the .dat file dat_file_path and sections it according to its categories
    #   Input:
    #       dat_file_path: string: full path to the .dat file to be read

    # read all the file lines
    file_lines = open(dat_file_path, "r").readlines()

    # define content variables
    file_title = []  # file title
    file_description = []  # file description (previously: header_content)
    file_categories = []  # all main categories in a list
    category_items = []  # items clustered by categories
    category_item_name = []  # name of item
    category_item_value = []  # value / values of item
    cmmindex = 0  # index for the cloning material map category
    matindex = 0  # index for the material category
    functindex = 0  # index for the function categories
    resdesindex = 0  # index for the result description category
    comment_lines = []  # lines with comments, marked with // -> not required

    # remove white spaces at the beginning and at the end of each line
    file_lines = [line.strip() for line in file_lines if line.strip()]

    # loop through all the lines of the file
    l = 0  # line index l
    category = (
        []
    )  # category variable -> used further down below for the sectioning of the file content
    while l < len(file_lines):
        match file_lines[l][0]:  # sectioning based on first character
            case "=":  # get file title
                curr_line_ind = l + 1
                while curr_line_ind < len(file_lines):
                    if file_lines[curr_line_ind][0] == "=":
                        l = curr_line_ind + 1
                        break
                    else:
                        file_title.append(file_lines[curr_line_ind])
                        curr_line_ind += 1
                        if curr_line_ind == len(file_lines):
                            raise Exception(
                                "The entire file was read without sectioning a file title"
                            )
            case (
                "-"
            ):  # Symbol indicates a new category -> The use of "-" as a bullet point in the file description is discussed below

                # add the old category (if not empty) and the read-in array items
                if (
                    (len(category) > 0)
                    and (len(category_item_name) > 0)
                    and (category != "TITLE")
                ):
                    file_categories.append(category)
                    # add array item name and value to the category_items
                    category_items.append([category_item_name, category_item_value])
                    # reset category_item_name and _value
                    category_item_name = []
                    category_item_value = []

                # get the new category
                first_letter_ind = file_lines[l].index(
                    re.findall("[A-Z]", file_lines[l])[0]
                )
                category = file_lines[l][first_letter_ind:]

                # if we have reached a FUNCT block, we reset its index counter
                if re.search("^FUNCT[0-9]+$", category):
                    functindex = 0

                # if we have reached the BC, we break out of the loop
                if category[0:6] == "DESIGN":
                    break
                # If the category is TITLE, we add the description of the file to file_description.
                #   As TITLE comes first, we have len(category)=0 and the description items
                #   are not added to category_items (see further above)
                if category[0:5] == "TITLE":  # add file description to file_description
                    curr_line_ind = l + 1
                    while curr_line_ind < len(file_lines):
                        if (file_lines[curr_line_ind][0] == "-") and (
                            file_lines[curr_line_ind].replace("-", "").isupper()
                        ):  # second condition in order to check if a new category comes up (- could also be used as a bullet point within the description) -> we check if we have an uppercase string by removing "---"
                            l = curr_line_ind  # -1 required?

                            # get the new category
                            first_letter_ind = file_lines[l].index(
                                re.findall("[A-Z]", file_lines[l])[0]
                            )
                            category = file_lines[l][first_letter_ind:]
                            break
                        else:
                            file_description.append(file_lines[curr_line_ind])
                            curr_line_ind += 1
                            if curr_line_ind == len(file_lines):
                                raise Exception(
                                    "The entire file was read without sectioning a file description"
                                )
                l += 1
            case "/":  # comment lines
                comment_lines.append(file_lines[l])
                l += 1
            case _:  # in a category
                if category == "MATERIALS":
                    matindex += 1
                    # NEW: split the line in "MAT <number>" as the name and the rest as the value
                    category_item_name.append(
                        re.findall("^MAT [0-9]+", file_lines[l])[0]
                    )
                    category_item_value.append(
                        file_lines[l].replace(
                            re.findall("^MAT [0-9]+ ", file_lines[l])[0], ""
                        )
                    )
                    """ old version, taken over from BACI_Converter.js
                    category_item_name, category_item_value =  # material_line_converter(file_lines[l], category_item_name, category_item_value)
                    """
                elif category == "CLONING MATERIAL MAP":
                    cmmindex += 1
                    category_item_value.append(
                        file_lines[l]
                    )  # the whole line is the value to append
                    category_item_name.append(cmmindex)  # the index is the name
                elif re.search(
                    "^FUNCT[0-9]+$", category
                ):  # NEW: we want to read the whole line of the category item, not only start and end value (otherwise we miss some information, e.g. "SYMBOLIC_FUNCTION_OF_SPACE_TIME")
                    functindex += 1
                    category_item_value.append(
                        file_lines[l]
                    )  # the whole line is the value to append
                    category_item_name.append(functindex)  # the index is the name
                elif (
                    category == "RESULT DESCRIPTION"
                ):  # NEW: we read whole lines for the result description section
                    resdesindex += 1
                    category_item_value.append(
                        file_lines[l]
                    )  # the whole line is the value to append
                    category_item_name.append(resdesindex)  # the index is the name
                else:
                    index_end_item = file_lines[l].index(" ")
                    index_begin_value = file_lines[l].rfind(" ")
                    category_item_name.append(
                        file_lines[l][0:index_end_item]
                    )  # item from first place to index_end_item
                    category_item_value.append(
                        file_lines[l][index_begin_value:]
                    )  # value from last blank to end

                l += 1

    # read in boundary conditions
    cond_entity_list = [
        [],
        [],
        [],
        [],
    ]  # sorted lists of condition entities clustered by POINT, LINE, SURF, VOL
    cond_type_list = [
        [],
        [],
        [],
        [],
    ]  # corresponding condition types for each of the condition entities (are lists by themselves, as an entity can have more than one condition)
    cond_context_list = [
        [],
        [],
        [],
        [],
    ]  # corresponding condition texts / contexts for each of the condition entities (are lists by themselves, as an entity can have more than one condition)
    count = 0
    cond = ""
    l = 0
    while l < len(file_lines):
        if (file_lines[l][0] == "-") and (
            file_lines[l][-10:] == "CONDITIONS"
        ):  # condition section reached
            count = -1
            first_letter = file_lines[l].index(re.findall("[A-Z]", file_lines[l])[0])
            cond = file_lines[l][first_letter:]
        elif (file_lines[l][0] == "-") and (
            file_lines[l][-10:] != "CONDITIONS"
        ):  # not a condition section
            count = 0
        elif count == -1:  # inside a condition section
            area = file_lines[l].split(" ")[0]
            if area == "DPOINT":
                count = 1
            if area == "DLINE":
                count = 2
            if area == "DSURF":
                count = 3
            if area == "DVOL":
                count = 4
        elif (count >= 1) and (file_lines[l][0] == "E"):  # entity line for a condition
            entity = int(file_lines[l].split(" ")[1])
            if entity not in cond_entity_list[count - 1]:
                cond_entity_list[count - 1].append(entity)
                cond_type_list[count - 1].append(
                    list([cond])
                )  # NEW -> we directly save it as a list, in order to have it homogenized
                cond_context_list[count - 1].append(
                    [file_lines[l][(file_lines[l].index("-") + 2) :]]
                )
            else:
                ind = cond_entity_list[count - 1].index(entity)
                if (
                    type(cond_type_list[count - 1][ind]) == str
                ):  # NEW: this case becomes irrelevant, see above
                    cond_type_list[count - 1][ind] = [
                        cond_type_list[count - 1][ind],
                        cond,
                    ]
                    cond_context_list[count - 1][ind] = [
                        cond_context_list[count - 1][ind],
                        file_lines[l][(file_lines[l].index("-") + 2) :],
                    ]
                else:
                    cond_type_list[count - 1][ind].append(cond)
                    cond_context_list[count - 1][ind].append(
                        file_lines[l][(file_lines[l].index("-") + 2) :]
                    )
        l += 1

    cond_entity_list, cond_type_list, cond_context_list = sort_conditions(
        cond_entity_list, cond_type_list, cond_context_list
    )

    # NEW: READ THE REST OF THE FILE (RELATED TO GEOMETRY)

    # get all file line indices with the regular expression ^-{2,}[A-Z0-9]+$ -> starting with at least two "-" and ending with a combination of uppercase letters and numbers
    geometry_categories_indices = [
        i
        for (i, l) in enumerate(file_lines)
        if (
            (len(re.findall("^-{2,}[A-Z0-9 -]+$", l)) > 0)
            and (l.replace("-", "") not in file_categories)
            and ("TITLE" not in l)
            and ("DESIGN" not in l)
        )
    ]

    # take all lines from the geometry_categories and save them in a geometry_lines list
    geometry_lines = [l for l in file_lines[geometry_categories_indices[0] :]]

    return_dict = {
        "file_title": file_title,
        "file_description": file_description,
        "file_categories": file_categories,
        "category_items": category_items,
        "cond_entity_list": cond_entity_list,
        "cond_type_list": cond_type_list,
        "cond_context_list": cond_context_list,
        "geometry_lines": geometry_lines,
    }
    return return_dict


def sort_conditions(src_cond_entity_list, src_cond_type_list, src_cond_context_list):
    # the function takes in condition lists, where the entities are unsorted numerically and sorts them accordingly

    # we use a copy of the lists
    cond_entity_list = src_cond_entity_list.copy()
    cond_type_list = src_cond_type_list.copy()
    cond_context_list = src_cond_context_list.copy()

    # sorting of the condition lists
    for i in range(len(cond_entity_list)):
        for j in range(len(cond_entity_list[i])):
            for k in range(j + 1, len(cond_entity_list[i])):
                if cond_entity_list[i][j] > cond_entity_list[i][k]:
                    temp = cond_entity_list[i][j]
                    cond_entity_list[i][j] = cond_entity_list[i][k]
                    cond_entity_list[i][k] = temp

                    temp = cond_type_list[i][j]
                    cond_type_list[i][j] = cond_type_list[i][k]
                    cond_type_list[i][k] = temp

                    temp = cond_context_list[i][j]
                    cond_context_list[i][j] = cond_context_list[i][k]
                    cond_context_list[i][k] = temp

    return cond_entity_list, cond_type_list, cond_context_list


def validate_dat_file_path(dat_file_path):
    # Validate the file path: file has to exist and end with ".dat"
    if not dat_file_path.endswith(".dat"):
        raise Exception("Provided file does not end with .dat!")

    if not os.path.exists(dat_file_path):
        raise Exception("Provided file does not exist!")


if __name__ == "__main__":
    ...
    # no need to implement anything here, as the method can only be called from within the main.py

from fourc_webviewer.input_file_utils.dat_file_visualization import function_plot_figure

import plotly

CLIENT_TYPE = "vue3"
if CLIENT_TYPE == "vue2":
    from trame.widgets import vuetify2 as vuetify
    from trame.ui.vuetify2 import SinglePageWithDrawerLayout
    from trame_vuetify.widgets.vuetify import HtmlElement
else:
    from trame.widgets import vuetify3 as vuetify
    from trame.ui.vuetify3 import SinglePageWithDrawerLayout
    from trame_vuetify.widgets.vuetify3 import HtmlElement
from trame.widgets import html, plotly, vtk


class VFileInput(HtmlElement):
    """Custom VFileInput element, since the one provided by trame does not currently support all relevant attributes, such as e.g. 'accept'.
    """


    def __init__(self, children=None, **kwargs):
        super().__init__("v-file-input", children, **kwargs)
        self._attr_names += [
            "accept",
            "append_icon",
            "append_outer_icon",
            "autofocus",
            "background_color",
            "chips",
            "clear_icon",
            "clearable",
            "color",
            "counter",
            "counter_size_string",
            "counter_string",
            "counter_value",  # JS functions unimplemented
            "dark",
            "dense",
            "disabled",
            "error",
            "error_count",
            "error_messages",
            "filled",
            "flat",
            "full_width",
            "height",
            "hide_details",
            "hide_input",
            "hide_spin_buttons",
            "hint",
            "id",
            "label",
            "light",
            "loader_height",
            "loading",
            "messages",
            "multiple",
            "outlined",
            "persistent_hint",
            "persistent_placeholder",
            "placeholder",
            "prefix",
            "prepend_icon",
            "prepend_inner_icon",
            "reverse",
            "rounded",
            "rules",
            "shaped",
            "show_size",
            "single_line",
            "small_chips",
            "solo",
            "solo_inverted",
            "success",
            "success_messages",
            "suffix",
            "truncate_length",
            "type",
            "validate_on_blur",
            "value",
        ]
        self._event_names += [
            "blur",
            "change",
            "click",
            ("click_append", "click:append"),
            ("click_append_outer", "click:append-outer"),
            ("click_clear", "click:clear"),
            ("click_prepend", "click:prepend"),
            ("click_prepend_inner", "click:prepend-inner"),
            "focus",
            "input",
            "keydown",
            "mousedown",
            "mouseup",
            ("update_error", "update:error"),
        ]

def _toolbar(server_controller):
    VFileInput(
        label=".dat file", 
        v_model=("INPUT_FILE",),
        update_modelValue="flushState('INPUT_FILE')",
        accept = ".dat"
        )
    vuetify.VBtn(
        text="CONVERT",
        v_show=("VTU_PATH == ''",),
        click=server_controller.CLICK_CONVERT_BUTTON,
    )
    vuetify.VBtn(
        text="INFO",
        outlined=True,
        color="red",
        v_show=("VTU_PATH != ''",),
        click=server_controller.CLICK_INFO_BUTTON,
    )
    vuetify.VBtn(
        text="EXPORT",
        outlined=True,
        color="blue",
        v_show=("VTU_PATH != ''",),
        click=server_controller.CLICK_EXPORT_BUTTON,
    )
    with vuetify.VBtn(icon=True, click=server_controller.VIEW_RESET_CAMERA):
        vuetify.VIcon("mdi-crop-free")


def _bottom_sheet_info():
    with vuetify.VBottomSheet(v_model=("INFO_MODE",), inset=True):
        with vuetify.VCard(
            classes="text-center",
            height=500,
        ):
            with vuetify.VCardText():
                html.H1(v_text=("TITLE",), v_if=("EDIT_MODE == EDIT_MODE_POSSIB[0]",))
                vuetify.VTextField(
                    v_model=("TITLE",), v_if=("EDIT_MODE == EDIT_MODE_POSSIB[1]",)
                )
                html.P(
                    v_for=(r"item in DESCRIPTION.split('\n')",),
                    v_text=("item",),
                    v_if=("EDIT_MODE == EDIT_MODE_POSSIB[0]",),
                )
                vuetify.VTextarea(
                    v_model=("DESCRIPTION",),
                    rows=17,  # default height of the element
                    v_if=("EDIT_MODE == EDIT_MODE_POSSIB[1]",),
                )


def _bottom_sheet_export(server_controller):
    with vuetify.VBottomSheet(v_model=("EXPORT_MODE",), inset=True):
        with vuetify.VCard(classes="text-center", height=250, title="Export"):
            with vuetify.VCardText():
                vuetify.VTextField(
                    label="Export .dat file", v_model=("EXPORT_DAT_PATH",)
                )
                vuetify.VAlert(
                   title="Click on <save> to export the changed .dat file under the entered path",
                   type="info", 
                   v_if  = ("EXPORT_STATUS == EXPORT_STATUS_POSSIB[0]", ),
                   classes = "h-50"
                )
                vuetify.VAlert(
                   title="Your file was exported correctly!",
                   type="success",
                   v_if  = ("EXPORT_STATUS == EXPORT_STATUS_POSSIB[1]", ),
                   classes = "h-50"
                )
                vuetify.VAlert(
                   title="There was a problem while trying to export! Check the entered path and the modified .dat file settings!",
                   type="error",
                   v_if  = ("EXPORT_STATUS == EXPORT_STATUS_POSSIB[2]", ),
                   classes = "h-50"
                )
        vuetify.VBtn(text="SAVE", color="primary", click=server_controller)


def _categories_dropdown():
    vuetify.VSelect(
        v_model=("SELECTED_MAIN_CATEGORY",),
        v_model_items=("MAIN_CATEGORIES",),
        __properties=[("v_model_items", "v-model:items")],
    )
    vuetify.VSelect(
        v_show=("AUX_CATEGORIES[SELECTED_MAIN_CATEGORY_INDEX].length>1"),
        v_model=("SELECTED_AUX_CATEGORY",),
        v_model_items=("AUX_CATEGORIES[SELECTED_MAIN_CATEGORY_INDEX]",),
        __properties=[("v_model_items", "v-model:items")],
    )


def _functions_panel(server):
    # dropdown with FUNCT names is already there (because FUNCT1, FUNCT2,... are treated as AUX_CATEGORIES of FUNCTIONS)

    # new dropdown for components
    vuetify.VSelect(
        v_model=("SELECTED_COMP",),
        items=("FUNCT[1][SELECTED_FUNCT_INDEX][0]",),
        v_show=("SELECTED_MAIN_CATEGORY == 'FUNCTIONS'",),
    )

    # infos regarding the component
    with vuetify.VTable(
        v_if=("SELECTED_MAIN_CATEGORY == 'FUNCTIONS'",),
    ):
        with html.Thead():
            with html.Tr():
                html.Th(
                    "Type",
                    classes="text-left font-weight-bold",
                )
                html.Th(
                    "Expression",
                    classes="text-left font-weight-bold",
                )

        with html.Tbody():
            with html.Tr(
                v_if="CATEGORIES.indexOf(SELECTED_AUX_CATEGORY) >=0",
            ):
                html.Td(
                    v_text=("FUNCT[1][SELECTED_FUNCT_INDEX][1][SELECTED_COMP_INDEX]",)
                )
                html.Td(
                    v_if="EDIT_MODE == EDIT_MODE_POSSIB[0]",
                    v_text=("FUNCT[1][SELECTED_FUNCT_INDEX][2][SELECTED_COMP_INDEX]",),
                )
                with html.Td(v_if="EDIT_MODE == EDIT_MODE_POSSIB[1]"):
                    vuetify.VTextField(
                        v_model=(
                            "FUNCT[1][SELECTED_FUNCT_INDEX][2][SELECTED_COMP_INDEX]",
                        ),
                        update_modelValue="flushState('FUNCT')",  # flush state to server
                    )

    # divider for optical separation
    vuetify.VDivider(
        thickness="20",
        v_if=("SELECTED_MAIN_CATEGORY == 'FUNCTIONS'",),
    )

    # numeric edit fields for the t_max,x,y,z values
    with vuetify.VTable(
        v_if=("SELECTED_MAIN_CATEGORY == 'FUNCTIONS'",),
    ):
        with html.Thead():
            with html.Tr():
                html.Th(
                    "Variable",
                    classes="text-left font-weight-bold",
                )
                html.Th(
                    "Value",
                    classes="text-left font-weight-bold",
                )
        with html.Tbody():
            with html.Tr():
                html.Td(
                    "t_max",
                    classes="text-left font-weight-bold",
                )
                with html.Td(
                    classes="text-center-md",
                ):
                    html.Input(
                        type="number",
                        v_model=("MAX_TIME",),
                    )
            with html.Tr():
                html.Td(
                    "x",
                    classes="text-left font-weight-bold",
                )
                with html.Td(
                    classes="text-center-md",
                ):
                    html.Input(type="number", v_model=("X_VAL",), classes="bg-gray")
            with html.Tr():
                html.Td(
                    "y",
                    classes="text-left font-weight-bold",
                )
                with html.Td(
                    classes="text-center-md",
                ):
                    html.Input(
                        type="number",
                        v_model=("Y_VAL",),
                    )
            with html.Tr():
                html.Td(
                    "z",
                    classes="text-left font-weight-bold",
                )
                with html.Td(
                    classes="text-center-md",
                ):
                    html.Input(
                        type="number",
                        v_model=("Z_VAL",),
                    )

    # plots of the components
    with vuetify.VContainer(v_show=("SELECTED_MAIN_CATEGORY == 'FUNCTIONS'",)):
        figure = plotly.Figure(
            display_logo=False,
            display_mode_bar="true",
        )
        server.controller.figure_update = figure.update
        server.controller.figure_update(function_plot_figure(server.state))


def _prop_value_table():
    with vuetify.VTable(
        v_if=("CONTENT_MODE == 'PROP_VALUE'",),
    ):
        with html.Thead():
            with html.Tr():
                html.Th(
                    "Property",
                    classes="text-left font-weight-bold",
                )
                html.Th(
                    "Value",
                    classes="text-left font-weight-bold",
                )

        with html.Tbody():

            with html.Tr(
                v_if="CATEGORIES.indexOf(SELECTED_AUX_CATEGORY) >=0",
                v_for="(item,i) in CATEGORY_ITEMS[CATEGORIES.indexOf(SELECTED_AUX_CATEGORY)][0]",
                key="i",
            ):
                html.Td(v_text=("item",))
                html.Td(
                    v_if="CATEGORIES.indexOf(SELECTED_AUX_CATEGORY) >=0 &&  EDIT_MODE == EDIT_MODE_POSSIB[0]",
                    v_text=(
                        "CATEGORY_ITEMS[CATEGORIES.indexOf(SELECTED_AUX_CATEGORY)][1][i]",
                    ),
                )
                with html.Td(
                    v_if="CATEGORIES.indexOf(SELECTED_AUX_CATEGORY) >=0 &&  EDIT_MODE == EDIT_MODE_POSSIB[1]",
                ):
                    vuetify.VTextField(
                        max_height=2,
                        v_model=(
                            "CATEGORY_ITEMS[CATEGORIES.indexOf(SELECTED_AUX_CATEGORY)][1][i]",
                        ),
                        update_modelValue="flushState('CATEGORY_ITEMS')",  # this is required in order to flush the state changes correctly to the server, as our passed on v-model is a nested variable
                    )


def _materials_panel():
    with vuetify.VCard(
        v_for="(mat_item, mat_i) in MATERIALS[0]",
        variant="outlined",
        classes="mt-4",
        v_show=("CONTENT_MODE == 'MATERIALS'",),
    ):
        with vuetify.VCardActions():
            html.Span(v_text=("MATERIALS[0][mat_i]"), classes="mr-10")
            html.Span(
                v_text=("MATERIALS[1][mat_i]"),
            )


def _cloning_material_map_panel():
    vuetify.VSelect(
        v_model=("SELECTED_CMM_LINE",),
        items=("CLONING_MATERIAL_MAP[0]",),
        v_show=("CONTENT_MODE == 'CLONING MATERIAL MAP'",),
    )
    with vuetify.VExpansionPanels(
        variant="popout", v_show=("CONTENT_MODE == 'CLONING MATERIAL MAP'",)
    ):
        with vuetify.VExpansionPanel(
            v_for="(src_or_tar_item,src_or_tar_i) in CLONING_MATERIAL_MAP[1][SELECTED_CMM_LINE_INDEX][0]",
            title=("src_or_tar_item",),
        ):
            with vuetify.VExpansionPanelText():
                with vuetify.VCard(
                    v_for="(line_item, line_ind) in CLONING_MATERIAL_MAP[1][SELECTED_CMM_LINE_INDEX][1][src_or_tar_i]",
                    variant="outlined",
                    classes="mt-4",
                ):
                    with vuetify.VCardActions():
                        html.Span(v_text=("MATERIALS[0][line_item]"), classes="mr-10")
                        # VIEW MODE
                        html.Span(
                            v_if="EDIT_MODE == EDIT_MODE_POSSIB[0]",
                            v_text=("MATERIALS[1][line_item]"),
                        )
                        # EDIT MODE
                        with vuetify.VTable(
                            v_if="EDIT_MODE == EDIT_MODE_POSSIB[1]",
                        ):
                            with html.Thead():
                                with html.Tr():
                                    html.Th(
                                        "Property",
                                        classes="text-left font-weight-bold",
                                    )
                                    html.Th(
                                        "Value",
                                        classes="text-left font-weight-bold",
                                    )

                            with html.Tbody():
                                with html.Tr(
                                    v_for="(mat_attr_item,mat_attr_index) in MATERIALS_MODIF_ATTR[line_item][0]",
                                    key="mat_attr_index",
                                ):
                                    html.Td(v_text=("mat_attr_item",))
                                    with html.Td(width=300):
                                        vuetify.VTextField(
                                            v_for="(component_item,  component_ind) in MATERIALS_MODIF_ATTR[line_item][1][mat_attr_index]",
                                            v_model=(
                                                "MATERIALS_MODIF_ATTR[line_item][1][mat_attr_index][component_ind]"
                                            ),
                                            update_modelValue="flushState('MATERIALS_MODIF_ATTR','MATERIALS')",
                                        )


def _materials_overview_panel():
    vuetify.VSelect(
        v_model=("SELECTED_CMM_LINE",),
        items=("CLONING_MATERIAL_MAP[0]",),
        v_show=("CONTENT_MODE == 'MATERIALS OVERVIEW'",),
    )
    with vuetify.VExpansionPanels(
        variant="popout", v_show=("CONTENT_MODE == 'MATERIALS OVERVIEW'",)
    ):
        with vuetify.VExpansionPanel(
            title=("CLONING_MATERIAL_MAP[1][SELECTED_CMM_LINE_INDEX][0]",),
        ):
            with vuetify.VExpansionPanelText():
                with vuetify.VCard(
                    v_for="(line_item, line_i) in CLONING_MATERIAL_MAP[1][SELECTED_CMM_LINE_INDEX][1]",
                    variant="outlined",
                    classes="mt-4",
                ):
                    with vuetify.VCardActions():
                        html.Span(v_text=("MATERIALS[0][line_item]"), classes="mr-10")
                        # VIEW MODE
                        html.Span(
                            v_if="EDIT_MODE == EDIT_MODE_POSSIB[0]",
                            v_text=("MATERIALS[1][line_item]"),
                        )
                        # EDIT MODE
                        with vuetify.VTable(
                            v_if="EDIT_MODE == EDIT_MODE_POSSIB[1]",
                        ):
                            with html.Thead():
                                with html.Tr():
                                    html.Th(
                                        "Property",
                                        classes="text-left font-weight-bold",
                                    )
                                    html.Th(
                                        "Value",
                                        classes="text-left font-weight-bold",
                                    )

                            with html.Tbody():
                                with html.Tr(
                                    v_for="(mat_attr_item,mat_attr_index) in MATERIALS_MODIF_ATTR[line_item][0]",
                                    key="mat_attr_index",
                                ):
                                    html.Td(v_text=("mat_attr_item",))
                                    with html.Td(width=300):
                                        vuetify.VTextField(
                                            v_for="(component_item,  component_ind) in MATERIALS_MODIF_ATTR[line_item][1][mat_attr_index]",
                                            v_model=(
                                                "MATERIALS_MODIF_ATTR[line_item][1][mat_attr_index][component_ind]"
                                            ),
                                            update_modelValue="flushState('MATERIALS_MODIF_ATTR','MATERIALS')",
                                        )


def _conditions_panel():
    # dropdown for general types: DPOINT DLINE DSURF DVOL
    vuetify.VSelect(
        v_show=("CONTENT_MODE == 'CONDITIONS'",),
        v_model=("SELECTED_COND_GENERAL_TYPE",),
        items=("COND_GENERAL_TYPES",),
    )

    # dropdown for entities of the general condition types
    vuetify.VSelect(
        v_if="CONTENT_MODE == 'CONDITIONS' && COND_ENTITY_LIST[SELECTED_COND_GENERAL_TYPE_INDEX].length > 0",
        v_model=("SELECTED_COND_ENTITY",),
        items=("COND_ENTITY_LIST[SELECTED_COND_GENERAL_TYPE_INDEX]",),
    )

    # table for each entity with the corresponding condition info
    with vuetify.VTable(
        v_if=("CONTENT_MODE == 'CONDITIONS'",),
    ):
        with html.Thead():
            with html.Tr():
                html.Th(
                    "Type",
                    classes="text-left font-weight-bold",
                )
                html.Th(
                    "Context",
                    classes="text-left font-weight-bold",
                )

        with html.Tbody():
            with html.Tr(
                v_if="CONTENT_MODE == 'CONDITIONS'",
                v_for=(
                    "(context_item, context_index) in COND_CONTEXT_LIST[SELECTED_COND_GENERAL_TYPE_INDEX][SELECTED_COND_ENTITY_INDEX]"
                ),
            ):
                html.Td(
                    v_text=(
                        "COND_TYPE_LIST[SELECTED_COND_GENERAL_TYPE_INDEX][SELECTED_COND_ENTITY_INDEX][context_index]",
                    )
                )
                html.Td(
                    v_if="EDIT_MODE == EDIT_MODE_POSSIB[0]", v_text=("context_item",)
                )
                with html.Td(
                    v_if="EDIT_MODE == EDIT_MODE_POSSIB[1]",
                ):
                    vuetify.VTextarea(
                        v_model=(
                            "COND_CONTEXT_LIST[SELECTED_COND_GENERAL_TYPE_INDEX][SELECTED_COND_ENTITY_INDEX][context_index]",
                        ),
                        rows=2,
                    )


def _result_description_panel():
    with vuetify.VCard(
        classes="mx-auto", v_if=("CONTENT_MODE == 'RESULT DESCRIPTION'",)
    ):
        with vuetify.VList(v_if="EDIT_MODE == EDIT_MODE_POSSIB[0]"):
            vuetify.VListItem(
                v_for="(line_item, line_ind) in RESULT_DESCRIPTION[1]",
                key=("line_ind",),
                value=("line_item",),
                v_text=("line_item",),
                active_color="#00B2B2",
                active=("line_ind === SELECTED_RESULT_DESCR_INDEX",),
                click="SELECTED_RESULT_DESCR_INDEX = line_ind",
            )
        vuetify.VTextField(
            v_if="EDIT_MODE == EDIT_MODE_POSSIB[1]",
            v_for="(line_item, line_ind) in RESULT_DESCRIPTION[1]",
            v_model=("RESULT_DESCRIPTION[1][line_ind]",),
            update_modelValue="flushState('RESULT_DESCRIPTION')",
        )


def create_gui(server, render_window):
    with SinglePageWithDrawerLayout(server) as layout:
        layout.title.set_text("4C Webviewer")

        with layout.toolbar as toolbar:
            toolbar.height = 100
            _toolbar(server.controller)

        with html.Div(v_show=("VTU_PATH != ''",)):
            _bottom_sheet_info()
            _bottom_sheet_export(server.controller.CLICK_SAVE_BUTTON)

        with layout.drawer as drawer:
            drawer.width = 800
            with html.Div(v_show=("VTU_PATH != ''",)):
                # EDIT MODE switch
                vuetify.VSwitch(
                    v_model=("EDIT_MODE", "EDIT_MODE_POSSIB[0]"),
                    label=("EDIT_MODE", "VIEW MODE"),
                    true_value=("EDIT_MODE_POSSIB[1]",),
                    false_value=("EDIT_MODE_POSSIB[0]",),
                    color="primary",
                    inset=True,
                    classes="ml-5",
                )

                # Further elements with conditional rendering (see above)
                _categories_dropdown()
                _prop_value_table()
                _materials_panel()
                _cloning_material_map_panel()
                _materials_overview_panel()
                _functions_panel(server)
                _conditions_panel()
                _result_description_panel()
            vuetify.VCard(
                title="No .dat file available",
                v_show=("VTU_PATH == ''",),
                classes="text-center",
                height="100%",
            )

        with layout.content:
            with vuetify.VContainer(
                fluid="true", classes="pa-0 fill-height", v_show=("VTU_PATH != ''",)
            ):
                html_view = vtk.VtkRemoteView(render_window)
                server.controller.VIEW_UPDATE = (
                    html_view.update
                )  # update function for the vtk figure
                server.controller.VIEW_RESET_CAMERA = html_view.reset_camera
                server.controller.on_server_ready.add(html_view.update)
                server.controller.on_server_ready.add(html_view.reset_camera)

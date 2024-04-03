## VTK
# import of vtk modules for the vtk pipelines
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor
from vtkmodules.vtkFiltersCore import (
    vtkThreshold,
    vtkThresholdPoints,
)
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)


# import required modules for interactor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa

import vtkmodules.vtkRenderingOpenGL2  # only needed for remote rendering

# import colors for vtk visualization
from vtkmodules.vtkCommonColor import vtkNamedColors


def create_vtu_reader():
    return vtkXMLUnstructuredGridReader()


def create_vtu_threshold(reader):
    vtu_threshold_mat = vtkThreshold()
    vtu_threshold_mat.SetInputConnection(reader.GetOutputPort())
    vtu_threshold_mat.SetInputArrayToProcess(
        0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_CELLS, "material"
    )

    return vtu_threshold_mat


def create_vtu_threshold_points(reader, server_state):
    vtu_threshold_condition_points = vtkThresholdPoints()
    vtu_threshold_condition_points.SetInputConnection(reader.GetOutputPort())
    vtu_threshold_condition_points.SetInputArrayToProcess(
        0,
        0,
        0,
        vtkDataObject.FIELD_ASSOCIATION_POINTS,
        f"{server_state.SELECTED_COND_GENERAL_TYPE.lower()}{server_state.SELECTED_COND_ENTITY}",
    )

    # this means we select all the nodes / points, where e.g. the field "dpoint1" has a value of 1. -> this effectively selects all points contained in the entity DPOINT 1
    vtu_threshold_condition_points.SetLowerThreshold(1.0)
    vtu_threshold_condition_points.SetUpperThreshold(1.0)

    return vtu_threshold_condition_points


def create_vtu_sphere(reader):
    vtu_sphere = vtkSphereSource()
    vtu_sphere.SetRadius(get_length_scale_rendered_object(reader) / 50.0)

    return vtu_sphere


def create_vtu_render_window(
    reader, vtu_threshold_condition_points, vtu_threshold_mat, vtu_sphere
):

    # create renderer
    renderer = vtkRenderer()
    renderWindow = vtkRenderWindow()
    renderWindow.AddRenderer(renderer)

    # create render window interactor
    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    # create mapper and actor for the entire geometry
    mapper_geom = vtkDataSetMapper()
    mapper_geom.SetInputConnection(reader.GetOutputPort())
    actor_geom = vtkActor()
    actor_geom.SetMapper(mapper_geom)
    # modify optical actor representation
    actor_geom.GetProperty().SetOpacity(0.2)
    actor_geom.GetProperty().SetColor(vtkNamedColors().GetColor3d("Bisque"))

    # assing threshold to a corresponding mapper and actor for the material highlighting
    mapper_mat = vtkDataSetMapper()
    mapper_mat.SetInputConnection(vtu_threshold_mat.GetOutputPort())
    actor_mat = vtkActor()
    actor_mat.SetMapper(mapper_mat)
    actor_mat.GetProperty().SetColor(vtkNamedColors().GetColor3d("venetian_red"))
    actor_mat.GetProperty().SetOpacity(0.7)

    # assing threshold to a corresponding mapper and actor for the node highlighting of prescribed conditions
    mapper_cond = vtkDataSetMapper()
    mapper_cond.SetInputConnection(vtu_threshold_condition_points.GetOutputPort())
    actor_cond = vtkActor()
    actor_cond.SetMapper(mapper_cond)
    actor_cond.GetProperty().SetColor(vtkNamedColors().GetColor3d("LimeGreen"))
    actor_cond.GetProperty().SetPointSize(
        get_length_scale_rendered_object(reader) * 50.0
    )
    actor_cond.GetProperty().SetOpacity(1.0)

    # assing sphere source object to represent the nodes where a result description is assigned to to the corresponding mapper and actor
    mapper_res_descr = vtkDataSetMapper()
    mapper_res_descr.SetInputConnection(vtu_sphere.GetOutputPort())
    actor_res_descr = vtkActor()
    actor_res_descr.SetMapper(mapper_res_descr)
    actor_res_descr.GetProperty().SetColor(vtkNamedColors().GetColor3d("Aqua"))

    # add the pipelines to the renderer and reset the camera
    renderer.AddActor(actor_geom)
    renderer.AddActor(actor_mat)
    renderer.AddActor(actor_cond)
    renderer.AddActor(actor_res_descr)
    renderer.SetBackground(vtkNamedColors().GetColor3d("White"))
    renderer.ResetCamera()

    return renderWindow


def update_vtu_reader(vtu_reader, vtu_file_path):
    # This function updates a given vtu reader with the corresponding vtu file path
    vtu_reader.SetFileName(vtu_file_path)
    vtu_reader.Update()


def get_length_scale_rendered_object(reader):
    # The function is used to extract a geometric length scale for the problem, which is used in the rendering process (e.g. to define the radius of the sphere source object representing the nodes in the "RESULT DESCRIPTION" section)
    #   Output:
    #       length_scale: maximum of the domain bound deltas [max_x-min_x, max_y-min_y, max_z-min_z]

    all_point_coords = [
        [
            reader.GetOutput().GetPoints().GetPoint(point_index)[0]
            for point_index in range(reader.GetOutput().GetPoints().GetNumberOfPoints())
        ],
        [
            reader.GetOutput().GetPoints().GetPoint(point_index)[1]
            for point_index in range(reader.GetOutput().GetPoints().GetNumberOfPoints())
        ],
        [
            reader.GetOutput().GetPoints().GetPoint(point_index)[2]
            for point_index in range(reader.GetOutput().GetPoints().GetNumberOfPoints())
        ],
    ]
    return max(
        [
            max(all_point_coords[0]) - min(all_point_coords[0]),
            max(all_point_coords[1]) - min(all_point_coords[1]),
            max(all_point_coords[2]) - min(all_point_coords[2]),
        ]
    )

"""Import modules"""
# import of vtk modules for the vtk pipelines
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
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

import re
import math

"""Global variables"""
vtu_global_cos_frac_scale_ = 1.0 / 5.0 # factor which scales the coordinate system axes with respect to the problem length scale
vtu_sphere_frac_scale_ = 1.0 / 50.0 # factor which scales the nodal result description with respect to the problem length scale
vtu_cond_marker_frac_scale_ = 50.0 # factor which scales the condition markers on points, lines, ... with respect to the problem length scale


"""VTU objects"""
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

    # scale using problem length scale
    vtu_sphere.SetRadius(get_length_scale_rendered_object(reader) * vtu_sphere_frac_scale_)

    return vtu_sphere

def create_vtu_global_cos(reader):
    vtu_global_cos = vtkAxesActor()
    vtu_global_cos.SetPosition(0,0,0)

    # scale using problem length scale
    scale_fac = get_length_scale_rendered_object(reader) * vtu_global_cos_frac_scale_
    vtu_global_cos.SetTotalLength(scale_fac, scale_fac, scale_fac)

    return vtu_global_cos


def create_vtu_render_window(
    reader, vtu_threshold_condition_points, vtu_threshold_mat, vtu_sphere, vtu_global_cos
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
        get_length_scale_rendered_object(reader) * vtu_cond_marker_frac_scale_
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
    renderer.AddActor(vtu_global_cos)
    renderer.SetBackground(vtkNamedColors().GetColor3d("White"))
    renderer.ResetCamera()

    return renderWindow

"""Update functions"""
def update_vtu_reader(vtu_reader, vtu_file_path):
    # This function updates a given vtu reader with the corresponding vtu file path
    vtu_reader.SetFileName(vtu_file_path)
    vtu_reader.Update()

def update_vtu_render_window(reader, sphere, global_cos, server):
    """Perform manual scaling of several render window objects.

    This is required, since some of the independent components, such as the vtkSphereSource,
    do not scale directly with our problem size.

    Args:
        reader (vtkXMLUnstructuredGridReader): grid reader
        sphere (vtkSphereSource): sphere used for the depiction of nodes with prescribed results
        global_cos (vtkAxesActor): global coordinate system
        server (trame server): server object of the application

    Returns:
        None 
    """ 


    ###   we need to update the vtkSphere, since it does not scale automatically with the new view
    # check if the line contains the marker "NODE"
    if len(re.findall("NODE", server.state.SELECTED_RESULT_DESCR)) > 0:
        # get the specified node
        result_descr_components = server.state.SELECTED_RESULT_DESCR.split(" ")
        node_index = (
            int(result_descr_components[result_descr_components.index("NODE") + 1]) - 1
        )

        # update graphic representation
        node_coords = reader.GetOutput().GetPoints().GetPoint(node_index)
        sphere.SetCenter(node_coords[0], node_coords[1], node_coords[2])
        # it is not required to update the actor_cond point size
        sphere.SetRadius(
            get_length_scale_rendered_object(reader) * vtu_sphere_frac_scale_
        )   

        # update the vtk figure
        server.controller.VIEW_UPDATE()

    ### we also need to update the axes lengths of the global COS
    scale_fac = get_length_scale_rendered_object(reader) * vtu_global_cos_frac_scale_
    global_cos.SetTotalLength(scale_fac, scale_fac, scale_fac)



def get_length_scale_rendered_object(reader):
    """Compute problem length scale from the bounds of the considered object.

    Args:
        reader (vtkXMLUnstructuredGridReader): grid reader
    Returns:
        float: maximum coordinate bound difference in 3-dimensions 

    """

    # get object bounds
    bounds = reader.GetOutput().GetBounds()

    # get maximum bound difference as the problem length scale
    return max(bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4])


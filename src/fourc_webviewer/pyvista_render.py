"""Import modules"""

import re
import pyvista as pv
from pyvista.trame.ui import plotter_ui

"""Global variables"""
PV_SPHERE_FRAC_SCALE = (
    1.0 / 50.0
)  # factor which scales the spheres used to represent nodal design conditions and result descriptions with respect to the problem length scale


def update_pv_plotter(
    pv_plotter,
    mesh,
    selected_material_mesh,
    selected_dc_geometry_entity,
    selected_result_description_node_coords,
):
    """Updates the pyvista plotter for the GUI.

    Args:
        mesh (pyvista.UnstructuredGrid): problem mesh
        selected_material_mesh (pyvista.UnstructuredGrid): mesh
                                                        component with
                                                        the selected
                                                        material.
        selected_dc_geometry_entity (pyvista.PointSet): set of points of
                                                        the geometric
                                                        entity for the
                                                        current design
                                                        condition selection.
        selected_result_description_node_coords (pyvista.pyvista_ndarray): array of
                                                            points (nodes) where the selected result description is prescribed.
    Returns:
        pyvista.Plotter(): plotter object to be integrated in the GUI

    """

    # clear plotter actors
    pv_plotter.clear_actors()

    # add mesh to plotter
    pv_plotter.add_mesh(mesh, color="bisque", opacity=0.2)

    # add selected material mesh to plotter
    pv_plotter.add_mesh(
        selected_material_mesh,
        color="darkorange",
        opacity=0.7,
        label="Selected material",
    )

    #  add selected design condition mesh to plotter
    dc_spheres = pv.MultiBlock()
    for i, point in enumerate(selected_dc_geometry_entity.points):
        sphere = pv.Sphere(
            center=point, radius=get_problem_length_scale(mesh) * PV_SPHERE_FRAC_SCALE
        )
        dc_spheres.append(sphere)
    pv_plotter.add_mesh(
        dc_spheres,
        color="navy",
        opacity=1.0,
        render_points_as_spheres=True,
        label="Selected design condition",
    )

    # add selected result description node to plotter
    pv_plotter.add_mesh(
        pv.Sphere(
            center=selected_result_description_node_coords,
            radius=get_problem_length_scale(mesh) * PV_SPHERE_FRAC_SCALE,
        ),
        color="deepskyblue",
        label="Selected result description",
    )

    # add plotter legend
    pv_plotter.add_legend()

    return pv_plotter


def get_problem_length_scale(pv_mesh):
    """Compute problem length scale from the bounds of the considered
    pyvista mesh.

    Args:
         pv_mesh (pyvista.UnstructuredGrid): geometry mesh
    Returns:
        float: maximum coordinate bound difference in 3-dimensions

    """

    # get maximum bound difference as the problem length scale
    return max(
        pv_mesh.bounds[1] - pv_mesh.bounds[0],
        pv_mesh.bounds[3] - pv_mesh.bounds[2],
        pv_mesh.bounds[5] - pv_mesh.bounds[4],
    )

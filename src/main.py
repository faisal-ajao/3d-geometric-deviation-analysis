import yaml
import numpy as np
import open3d as o3d
import pyvista as pv
import matplotlib.pyplot as plt

# ======================================================
# Load Configuration
# ======================================================
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

point_cloud_file = config["input_pcd_path"]
mesh_file = config["input_mesh_path"]
point_size = config["point_size"]
hist_output_path = config["histogram_output_path"]


# ======================================================
# Create Styled Feature Histogram
# ======================================================
def hist_styled(feature, f_name):
    # Create histogram
    n, bins, patches = plt.hist(
        feature,
        bins=100,
        facecolor="#2ab0ff",
        edgecolor="#e0e0e0",
        linewidth=0.5,
        alpha=0.7,
        zorder=4,
    )
    n = n.astype("int")

    # Color histogram bars according to their frequencies
    for i in range(len(patches)):
        patches[i].set_facecolor(plt.cm.cool(n[i] / max(n)))

    # Calculate statistical values
    mean_val = np.mean(feature)
    median_val = np.median(feature)
    mode_val = (bins[np.argmax(n)] + bins[np.argmax(n) + 1]) / 2

    # Add vertical lines for mean, median and mode
    plt.axvline(
        mean_val,
        color="lightcoral",
        linestyle="dashed",
        linewidth=2,
        label=f"Mean: {mean_val:.3f}",
        zorder=5,
    )
    plt.axvline(
        median_val,
        color="palegreen",
        linestyle="dashed",
        linewidth=2,
        label=f"Median: {median_val:.3f}",
        zorder=5,
    )
    plt.axvline(
        mode_val,
        color="skyblue",
        linestyle="dashed",
        linewidth=2,
        label=f"Mode: {mode_val:.3f}",
        zorder=5,
    )

    # Set title and axis labels
    plt.title(f"{f_name}-feature: Distribution", fontsize=10)
    plt.xlabel(f"{f_name} values", fontsize=10)
    plt.ylabel("Point Numbers", fontsize=10)

    # Add grid
    plt.grid(True, c="grey", ls="--", lw=0.2, zorder=0)

    # Add legend
    plt.legend(fontsize=7)

    # Export histogram
    plt.savefig(hist_output_path)

    plt.show()
    return


# ======================================================
# Load Point Cloud and Reference Mesh
# ======================================================
def compute_distance_to_mesh(point_cloud_file, mesh_file):
    # Load point cloud
    point_cloud = o3d.io.read_point_cloud(point_cloud_file)
    if point_cloud.is_empty():
        raise ValueError("Point cloud is empty or failed to load.")

    # Load reference triangle mesh
    mesh = o3d.io.read_triangle_mesh(mesh_file)
    if mesh.is_empty() or not mesh.has_triangles():
        raise ValueError("Mesh is empty or has no triangles.")

    # Convert legacy mesh to tensor mesh for distance computation
    mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)

    # Create a raycasting scene and add the reference mesh
    scene = o3d.t.geometry.RaycastingScene()
    _ = scene.add_triangles(mesh_t)

    # Convert point cloud coordinates into an Open3D tensor
    points = o3d.core.Tensor(
        np.asarray(point_cloud.points), dtype=o3d.core.Dtype.Float32
    )

    # Compute the distance of each point from the mesh surface
    try:
        distances = scene.compute_distance(points).numpy()
    except Exception as e:
        raise RuntimeError(f"Distance calculation failed: {e}")

    return point_cloud, distances


# ======================================================
# Compute Point-to-Mesh Distances
# ======================================================
point_cloud, distances = compute_distance_to_mesh(point_cloud_file, mesh_file)


# ======================================================
# Initialize Point Cloud and Mesh Visualization
# ======================================================
plotter = pv.Plotter()

# Load reference mesh for PyVista visualization
mesh = pv.read(mesh_file)
mesh.plot(full_screen=True)

# Convert Open3D point cloud coordinates into a PyVista point cloud
points = np.asarray(point_cloud.points)
pcd_pv = pv.PolyData(points)
pcd_pv.plot(full_screen=True, point_size=point_size)

# Attach computed distances as point data
pcd_pv["distance"] = distances


# ======================================================
# Configure Distance Visualization Range
# ======================================================
feature_min = np.nanmin(distances)
feature_max = np.nanmax(distances)

# Display point cloud colored according to distance values
actor = plotter.add_mesh(
    pcd_pv,
    scalars="distance",
    cmap="jet",
    point_size=point_size,
    clim=[feature_min, feature_max],
)

# Display reference mesh
plotter.add_mesh(mesh)


# ======================================================
# Update Point Cloud Segmentation from Threshold Slider
# ======================================================
def update_slider(threshold):
    global segmented_point_cloud

    # Select points whose distance is greater than or equal to the threshold
    mask = pcd_pv["distance"] >= threshold

    # Extract the selected points
    segmented_point_cloud = pcd_pv.extract_points(mask).cast_to_poly_points()

    # Update the displayed point cloud with the selected points
    actor.mapper.dataset = segmented_point_cloud


# ======================================================
# Initialize Interactive Distance Segmentation
# ======================================================
plotter.add_slider_widget(
    update_slider,
    [feature_min, feature_max],
    value=feature_min,
    title="Minimum Deviation",
)

# ======================================================
# Interactive Point Cloud Visualization
# ======================================================
plotter.show(full_screen=True)


# ======================================================
# Generate Distance Distribution Histogram
# ======================================================
hist_styled(distances, "Distance to mesh")

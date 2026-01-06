#!/usr/bin/env python3
"""
Update the wooden model (boy_Rigging_smplx_tex.fbx) joint positions to match lod1.fbx.

This creates a new dump_wooden dataset with:
- Joint positions from lod1.fbx (properly extracted)
- Mesh vertices scaled/transformed to match lod1 proportions
- Original wooden mesh topology and skin weights

Usage:
    python scripts/update_wooden_to_lod1_positions.py
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import fbx
    import FbxCommon
except ImportError:
    print("FBX SDK is required")
    sys.exit(1)


# SMPL-H joint order
SMPLH_JOINTS = [
    "Pelvis", "L_Hip", "R_Hip", "Spine1", "L_Knee", "R_Knee", "Spine2",
    "L_Ankle", "R_Ankle", "Spine3", "L_Foot", "R_Foot", "Neck",
    "L_Collar", "R_Collar", "Head", "L_Shoulder", "R_Shoulder",
    "L_Elbow", "R_Elbow", "L_Wrist", "R_Wrist",
    "L_Index1", "L_Index2", "L_Index3", "L_Middle1", "L_Middle2", "L_Middle3",
    "L_Pinky1", "L_Pinky2", "L_Pinky3", "L_Ring1", "L_Ring2", "L_Ring3",
    "L_Thumb1", "L_Thumb2", "L_Thumb3",
    "R_Index1", "R_Index2", "R_Index3", "R_Middle1", "R_Middle2", "R_Middle3",
    "R_Pinky1", "R_Pinky2", "R_Pinky3", "R_Ring1", "R_Ring2", "R_Ring3",
    "R_Thumb1", "R_Thumb2", "R_Thumb3",
]

# lod1 bone names to SMPL-H names
LOD1_TO_SMPLH = {
    "root": "Pelvis",
    "l_upleg": "L_Hip", "r_upleg": "R_Hip",
    "c_spine0": "Spine1",
    "l_lowleg": "L_Knee", "r_lowleg": "R_Knee",
    "c_spine1": "Spine2",
    "l_foot": "L_Ankle", "r_foot": "R_Ankle",
    "c_spine3": "Spine3",
    "l_ball": "L_Foot", "r_ball": "R_Foot",
    "c_neck": "Neck",
    "l_clavicle": "L_Collar", "r_clavicle": "R_Collar",
    "c_head": "Head",
    "l_uparm": "L_Shoulder", "r_uparm": "R_Shoulder",
    "l_lowarm": "L_Elbow", "r_lowarm": "R_Elbow",
    "l_wrist": "L_Wrist", "r_wrist": "R_Wrist",
    "l_index1": "L_Index1", "l_index2": "L_Index2", "l_index3": "L_Index3",
    "l_middle1": "L_Middle1", "l_middle2": "L_Middle2", "l_middle3": "L_Middle3",
    "l_ring1": "L_Ring1", "l_ring2": "L_Ring2", "l_ring3": "L_Ring3",
    "l_pinky1": "L_Pinky1", "l_pinky2": "L_Pinky2", "l_pinky3": "L_Pinky3",
    "l_thumb1": "L_Thumb1", "l_thumb2": "L_Thumb2", "l_thumb3": "L_Thumb3",
    "r_index1": "R_Index1", "r_index2": "R_Index2", "r_index3": "R_Index3",
    "r_middle1": "R_Middle1", "r_middle2": "R_Middle2", "r_middle3": "R_Middle3",
    "r_ring1": "R_Ring1", "r_ring2": "R_Ring2", "r_ring3": "R_Ring3",
    "r_pinky1": "R_Pinky1", "r_pinky2": "R_Pinky2", "r_pinky3": "R_Pinky3",
    "r_thumb1": "R_Thumb1", "r_thumb2": "R_Thumb2", "r_thumb3": "R_Thumb3",
}

SMPLH_KINTREE = [
    -1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19,
    20, 22, 23, 20, 25, 26, 20, 28, 29, 20, 31, 32, 20, 34, 35,
    21, 37, 38, 21, 40, 41, 21, 43, 44, 21, 46, 47, 21, 49, 50,
]


def collect_nodes(node, nodes_dict=None):
    if nodes_dict is None:
        nodes_dict = {}
    nodes_dict[node.GetName()] = node
    for i in range(node.GetChildCount()):
        collect_nodes(node.GetChild(i), nodes_dict)
    return nodes_dict


def extract_lod1_joint_positions(lod1_path):
    """Extract joint positions from lod1.fbx."""
    manager, scene = FbxCommon.InitializeSdkObjects()
    result = FbxCommon.LoadScene(manager, scene, lod1_path)

    if not result:
        print("Failed to load lod1.fbx")
        manager.Destroy()
        return None

    all_nodes = collect_nodes(scene.GetRootNode())

    j_template = np.zeros((52, 3), dtype=np.float32)

    for lod1_name, smplh_name in LOD1_TO_SMPLH.items():
        if lod1_name not in all_nodes:
            continue
        if smplh_name not in SMPLH_JOINTS:
            continue

        node = all_nodes[lod1_name]
        transform = node.EvaluateGlobalTransform()
        translation = transform.GetT()

        joint_idx = SMPLH_JOINTS.index(smplh_name)
        j_template[joint_idx] = [
            translation[0] / 100.0,
            translation[1] / 100.0,
            translation[2] / 100.0,
        ]

    manager.Destroy()
    return j_template


def extract_wooden_mesh_data(wooden_path):
    """Extract mesh data from wooden model."""
    manager, scene = FbxCommon.InitializeSdkObjects()
    result = FbxCommon.LoadScene(manager, scene, wooden_path)

    if not result:
        print("Failed to load wooden model")
        manager.Destroy()
        return None

    # Find mesh node
    def find_mesh(node):
        attr = node.GetNodeAttribute()
        if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.EType.eMesh:
            return node
        for i in range(node.GetChildCount()):
            result = find_mesh(node.GetChild(i))
            if result:
                return result
        return None

    mesh_node = find_mesh(scene.GetRootNode())
    if not mesh_node:
        print("No mesh found")
        manager.Destroy()
        return None

    mesh = mesh_node.GetNodeAttribute()
    num_verts = mesh.GetControlPointsCount()

    # Extract vertices (convert from cm to m)
    control_points = mesh.GetControlPoints()
    vertices = np.zeros((num_verts, 3), dtype=np.float32)
    for i in range(num_verts):
        cp = control_points[i]
        vertices[i] = [cp[0] / 100.0, cp[1] / 100.0, cp[2] / 100.0]

    # Extract faces
    num_polys = mesh.GetPolygonCount()
    faces = []
    for i in range(num_polys):
        poly_size = mesh.GetPolygonSize(i)
        if poly_size == 3:
            faces.append([
                mesh.GetPolygonVertex(i, 0),
                mesh.GetPolygonVertex(i, 1),
                mesh.GetPolygonVertex(i, 2),
            ])
        elif poly_size == 4:
            faces.append([mesh.GetPolygonVertex(i, 0), mesh.GetPolygonVertex(i, 1), mesh.GetPolygonVertex(i, 2)])
            faces.append([mesh.GetPolygonVertex(i, 0), mesh.GetPolygonVertex(i, 2), mesh.GetPolygonVertex(i, 3)])
    faces = np.array(faces, dtype=np.uint16)

    # Extract UVs
    uvs = np.zeros((num_verts, 2), dtype=np.float32)
    uv_element = mesh.GetElementUV(0) if mesh.GetElementUVCount() > 0 else None
    if uv_element:
        direct_array = uv_element.GetDirectArray()
        mapping_mode = uv_element.GetMappingMode()
        reference_mode = uv_element.GetReferenceMode()

        if mapping_mode == fbx.FbxLayerElement.EMappingMode.eByControlPoint:
            for i in range(num_verts):
                if reference_mode == fbx.FbxLayerElement.EReferenceMode.eDirect:
                    uv = direct_array.GetAt(i)
                else:
                    idx = uv_element.GetIndexArray().GetAt(i)
                    uv = direct_array.GetAt(idx)
                uvs[i] = [uv[0], uv[1]]

    # Extract skin weights
    skin_weights = np.zeros((num_verts, 4), dtype=np.float32)
    skin_indices = np.zeros((num_verts, 4), dtype=np.uint16)

    skin_count = mesh.GetDeformerCount(fbx.FbxDeformer.EDeformerType.eSkin)
    if skin_count > 0:
        skin = mesh.GetDeformer(0, fbx.FbxDeformer.EDeformerType.eSkin)

        # Collect weights per vertex
        vertex_weights = {i: [] for i in range(num_verts)}

        for c in range(skin.GetClusterCount()):
            cluster = skin.GetCluster(c)
            link_node = cluster.GetLink()
            if not link_node:
                continue

            joint_name = link_node.GetName()
            if joint_name not in SMPLH_JOINTS:
                continue

            joint_idx = SMPLH_JOINTS.index(joint_name)
            indices = cluster.GetControlPointIndices()
            weights = cluster.GetControlPointWeights()

            for i in range(cluster.GetControlPointIndicesCount()):
                vi = indices[i]
                w = weights[i]
                if w > 0:
                    vertex_weights[vi].append((joint_idx, w))

        # Take top 4 weights per vertex
        for vi in range(num_verts):
            weights = sorted(vertex_weights[vi], key=lambda x: -x[1])[:4]
            total = sum(w for _, w in weights)
            if total > 0:
                for i, (joint_idx, w) in enumerate(weights):
                    skin_indices[vi, i] = joint_idx
                    skin_weights[vi, i] = w / total

    # Extract original joint positions (convert from cm to m)
    all_nodes = collect_nodes(scene.GetRootNode())
    j_original = np.zeros((52, 3), dtype=np.float32)

    for joint_name in SMPLH_JOINTS:
        if joint_name not in all_nodes:
            continue
        joint_idx = SMPLH_JOINTS.index(joint_name)
        node = all_nodes[joint_name]
        transform = node.EvaluateGlobalTransform()
        translation = transform.GetT()
        # Convert from cm to m
        j_original[joint_idx] = [translation[0] / 100.0, translation[1] / 100.0, translation[2] / 100.0]

    manager.Destroy()

    return {
        "vertices": vertices,
        "faces": faces,
        "uvs": uvs,
        "skin_weights": skin_weights,
        "skin_indices": skin_indices,
        "j_original": j_original,
    }


def transform_mesh_to_match_skeleton(vertices, skin_indices, skin_weights, j_old, j_new):
    """
    Transform mesh vertices to match new joint positions.

    Uses Linear Blend Skinning approach:
    For each vertex, compute weighted average of transformations from its influencing bones.
    """
    num_verts = vertices.shape[0]
    new_vertices = np.zeros_like(vertices)

    for vi in range(num_verts):
        # Get the bone indices and weights for this vertex
        indices = skin_indices[vi]
        weights = skin_weights[vi]

        # Compute weighted average of bone displacements
        total_weight = 0
        weighted_displacement = np.zeros(3)

        for i in range(4):
            bone_idx = indices[i]
            weight = weights[i]

            if weight > 0:
                # Get old and new bone positions
                old_pos = j_old[bone_idx]
                new_pos = j_new[bone_idx]

                # Compute displacement
                displacement = new_pos - old_pos

                weighted_displacement += weight * displacement
                total_weight += weight

        # Apply weighted displacement to vertex
        if total_weight > 0:
            new_vertices[vi] = vertices[vi] + weighted_displacement
        else:
            new_vertices[vi] = vertices[vi]

    return new_vertices


def main():
    lod1_path = str(PROJECT_ROOT / "assets" / "lod1.fbx")
    wooden_path = str(PROJECT_ROOT / "assets" / "wooden_models" / "boy_Rigging_smplx_tex.fbx")
    output_dir = str(PROJECT_ROOT / "scripts" / "gradio" / "static" / "assets" / "dump_lod1")

    print(f"Loading lod1.fbx joint positions...")
    j_lod1 = extract_lod1_joint_positions(lod1_path)
    if j_lod1 is None:
        return 1

    print(f"Loading wooden model mesh data...")
    wooden_data = extract_wooden_mesh_data(wooden_path)
    if wooden_data is None:
        return 1

    print(f"\nOriginal wooden mesh: {wooden_data['vertices'].shape[0]} vertices")
    print(f"Original wooden joints: {wooden_data['j_original'].shape}")

    # Transform vertices to match lod1 skeleton
    print("\nTransforming mesh vertices to match lod1 skeleton...")
    new_vertices = transform_mesh_to_match_skeleton(
        wooden_data['vertices'],
        wooden_data['skin_indices'],
        wooden_data['skin_weights'],
        wooden_data['j_original'],
        j_lod1,
    )

    print(f"Old vertex Y range: [{wooden_data['vertices'][:,1].min():.3f}, {wooden_data['vertices'][:,1].max():.3f}]")
    print(f"New vertex Y range: [{new_vertices[:,1].min():.3f}, {new_vertices[:,1].max():.3f}]")
    print(f"Lod1 joint Y range: [{j_lod1[:,1].min():.3f}, {j_lod1[:,1].max():.3f}]")

    # Save data
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "v_template.bin"), "wb") as f:
        f.write(new_vertices.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "faces.bin"), "wb") as f:
        f.write(wooden_data['faces'].flatten().astype(np.uint16).tobytes())

    with open(os.path.join(output_dir, "uvs.bin"), "wb") as f:
        f.write(wooden_data['uvs'].flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "skinWeights.bin"), "wb") as f:
        f.write(wooden_data['skin_weights'].flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "skinIndice.bin"), "wb") as f:
        f.write(wooden_data['skin_indices'].flatten().astype(np.uint16).tobytes())

    with open(os.path.join(output_dir, "j_template.bin"), "wb") as f:
        f.write(j_lod1.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "keypoints.bin"), "wb") as f:
        f.write(j_lod1.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "kintree.bin"), "wb") as f:
        f.write(np.array(SMPLH_KINTREE, dtype=np.int32).tobytes())

    with open(os.path.join(output_dir, "joint_names.json"), "w") as f:
        json.dump(SMPLH_JOINTS, f, indent=2)

    print(f"\nSaved to {output_dir}")
    print(f"  Vertices: {new_vertices.shape}")
    print(f"  Faces: {wooden_data['faces'].shape}")
    print(f"  Skin weights: {wooden_data['skin_weights'].shape}")
    print(f"  Joint template: {j_lod1.shape}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

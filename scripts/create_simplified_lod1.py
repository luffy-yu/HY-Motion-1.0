#!/usr/bin/env python3
"""
Create a simplified lod1 FBX file with only 52 SMPL-H joints.

This script uses the FBX SDK to:
1. Load lod1.fbx
2. Create a new FBX with simplified 52-joint skeleton
3. Properly transfer and normalize skin weights
4. Export the simplified FBX

Usage:
    python scripts/create_simplified_lod1.py
"""

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


# lod1.fbx bone name to SMPL-H joint name mapping
# Each lod1 bone maps to exactly one SMPL-H joint
LOD1_TO_SMPLH = {
    # Main body
    "root": "Pelvis",
    "l_upleg": "L_Hip",
    "r_upleg": "R_Hip",
    "c_spine0": "Spine1",
    "l_lowleg": "L_Knee",
    "r_lowleg": "R_Knee",
    "c_spine1": "Spine2",
    "c_spine2": "Spine2",  # merge with Spine2
    "l_foot": "L_Ankle",
    "r_foot": "R_Ankle",
    "c_spine3": "Spine3",
    "l_ball": "L_Foot",
    "r_ball": "R_Foot",
    "c_neck": "Neck",
    "l_clavicle": "L_Collar",
    "r_clavicle": "R_Collar",
    "c_head": "Head",
    "c_jaw": "Head",
    "l_uparm": "L_Shoulder",
    "r_uparm": "R_Shoulder",
    "l_lowarm": "L_Elbow",
    "r_lowarm": "R_Elbow",
    "l_wrist": "L_Wrist",
    "r_wrist": "R_Wrist",
    "l_wrist_twist": "L_Wrist",
    "r_wrist_twist": "R_Wrist",
    # Foot detail bones
    "l_transversetarsal": "L_Foot",
    "r_transversetarsal": "R_Foot",
    "l_talocrural": "L_Ankle",
    "r_talocrural": "R_Ankle",
    "l_subtalar": "L_Ankle",
    "r_subtalar": "R_Ankle",
    # Twist bones - upper leg
    "l_upleg_twist0_proc": "L_Hip",
    "l_upleg_twist1_proc": "L_Hip",
    "l_upleg_twist2_proc": "L_Hip",
    "l_upleg_twist3_proc": "L_Hip",
    "l_upleg_twist4_proc": "L_Hip",
    "r_upleg_twist0_proc": "R_Hip",
    "r_upleg_twist1_proc": "R_Hip",
    "r_upleg_twist2_proc": "R_Hip",
    "r_upleg_twist3_proc": "R_Hip",
    "r_upleg_twist4_proc": "R_Hip",
    # Twist bones - lower leg
    "l_lowleg_twist1_proc": "L_Knee",
    "l_lowleg_twist2_proc": "L_Knee",
    "l_lowleg_twist3_proc": "L_Knee",
    "l_lowleg_twist4_proc": "L_Knee",
    "r_lowleg_twist1_proc": "R_Knee",
    "r_lowleg_twist2_proc": "R_Knee",
    "r_lowleg_twist3_proc": "R_Knee",
    "r_lowleg_twist4_proc": "R_Knee",
    # Twist bones - upper arm
    "l_uparm_twist0_proc": "L_Shoulder",
    "l_uparm_twist1_proc": "L_Shoulder",
    "l_uparm_twist2_proc": "L_Shoulder",
    "l_uparm_twist3_proc": "L_Shoulder",
    "l_uparm_twist4_proc": "L_Shoulder",
    "r_uparm_twist0_proc": "R_Shoulder",
    "r_uparm_twist1_proc": "R_Shoulder",
    "r_uparm_twist2_proc": "R_Shoulder",
    "r_uparm_twist3_proc": "R_Shoulder",
    "r_uparm_twist4_proc": "R_Shoulder",
    # Twist bones - lower arm
    "l_lowarm_twist1_proc": "L_Elbow",
    "l_lowarm_twist2_proc": "L_Elbow",
    "l_lowarm_twist3_proc": "L_Elbow",
    "l_lowarm_twist4_proc": "L_Elbow",
    "r_lowarm_twist1_proc": "R_Elbow",
    "r_lowarm_twist2_proc": "R_Elbow",
    "r_lowarm_twist3_proc": "R_Elbow",
    "r_lowarm_twist4_proc": "R_Elbow",
    # Neck twist
    "c_neck_twist0_proc": "Neck",
    "c_neck_twist1_proc": "Neck",
    # Fingers - left
    "l_index1": "L_Index1",
    "l_index2": "L_Index2",
    "l_index3": "L_Index3",
    "l_index_null": "L_Index3",
    "l_middle1": "L_Middle1",
    "l_middle2": "L_Middle2",
    "l_middle3": "L_Middle3",
    "l_middle_null": "L_Middle3",
    "l_ring1": "L_Ring1",
    "l_ring2": "L_Ring2",
    "l_ring3": "L_Ring3",
    "l_ring_null": "L_Ring3",
    "l_pinky0": "L_Pinky1",
    "l_pinky1": "L_Pinky1",
    "l_pinky2": "L_Pinky2",
    "l_pinky3": "L_Pinky3",
    "l_pinky_null": "L_Pinky3",
    "l_thumb0": "L_Thumb1",
    "l_thumb1": "L_Thumb1",
    "l_thumb2": "L_Thumb2",
    "l_thumb3": "L_Thumb3",
    "l_thumb_null": "L_Thumb3",
    # Fingers - right
    "r_index1": "R_Index1",
    "r_index2": "R_Index2",
    "r_index3": "R_Index3",
    "r_index_null": "R_Index3",
    "r_middle1": "R_Middle1",
    "r_middle2": "R_Middle2",
    "r_middle3": "R_Middle3",
    "r_middle_null": "R_Middle3",
    "r_ring1": "R_Ring1",
    "r_ring2": "R_Ring2",
    "r_ring3": "R_Ring3",
    "r_ring_null": "R_Ring3",
    "r_pinky0": "R_Pinky1",
    "r_pinky1": "R_Pinky1",
    "r_pinky2": "R_Pinky2",
    "r_pinky3": "R_Pinky3",
    "r_pinky_null": "R_Pinky3",
    "r_thumb0": "R_Thumb1",
    "r_thumb1": "R_Thumb1",
    "r_thumb2": "R_Thumb2",
    "r_thumb3": "R_Thumb3",
    "r_thumb_null": "R_Thumb3",
}

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

SMPLH_KINTREE = [
    -1,  # 0: Pelvis
    0, 0, 0,  # 1-3: L_Hip, R_Hip, Spine1
    1, 2, 3,  # 4-6: L_Knee, R_Knee, Spine2
    4, 5, 6,  # 7-9: L_Ankle, R_Ankle, Spine3
    7, 8, 9, 9, 9, 12,  # 10-15: L_Foot, R_Foot, Neck, L_Collar, R_Collar, Head
    13, 14, 16, 17, 18, 19,  # 16-21: L_Shoulder, R_Shoulder, L_Elbow, R_Elbow, L_Wrist, R_Wrist
    # Left hand
    20, 22, 23,  # L_Index1/2/3
    20, 25, 26,  # L_Middle1/2/3
    20, 28, 29,  # L_Pinky1/2/3
    20, 31, 32,  # L_Ring1/2/3
    20, 34, 35,  # L_Thumb1/2/3
    # Right hand
    21, 37, 38,  # R_Index1/2/3
    21, 40, 41,  # R_Middle1/2/3
    21, 43, 44,  # R_Pinky1/2/3
    21, 46, 47,  # R_Ring1/2/3
    21, 49, 50,  # R_Thumb1/2/3
]


def collect_nodes(node, nodes_dict=None):
    """Recursively collect all nodes."""
    if nodes_dict is None:
        nodes_dict = {}
    nodes_dict[node.GetName()] = node
    for i in range(node.GetChildCount()):
        collect_nodes(node.GetChild(i), nodes_dict)
    return nodes_dict


def find_mesh_node(node):
    """Find the mesh node in the scene."""
    attr = node.GetNodeAttribute()
    if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.EType.eMesh:
        return node
    for i in range(node.GetChildCount()):
        result = find_mesh_node(node.GetChild(i))
        if result:
            return result
    return None


def extract_simplified_skin_data(mesh_node, lod1_to_smplh_idx):
    """
    Extract skin weights and map them to simplified SMPL-H skeleton.

    Returns per-vertex weights for the 52 SMPL-H joints.
    """
    mesh = mesh_node.GetNodeAttribute()
    num_verts = mesh.GetControlPointsCount()

    # Accumulate weights for each SMPL-H joint
    smplh_weights = np.zeros((num_verts, 52), dtype=np.float64)

    skin_count = mesh.GetDeformerCount(fbx.FbxDeformer.EDeformerType.eSkin)
    if skin_count == 0:
        print("Warning: No skin deformer found")
        return smplh_weights

    skin = mesh.GetDeformer(0, fbx.FbxDeformer.EDeformerType.eSkin)
    cluster_count = skin.GetClusterCount()

    mapped_count = 0
    unmapped_bones = set()

    for c in range(cluster_count):
        cluster = skin.GetCluster(c)
        link_node = cluster.GetLink()
        if not link_node:
            continue

        bone_name = link_node.GetName()

        # Map to SMPL-H joint index
        if bone_name in lod1_to_smplh_idx:
            smplh_idx = lod1_to_smplh_idx[bone_name]
            mapped_count += 1

            indices = cluster.GetControlPointIndices()
            weights = cluster.GetControlPointWeights()

            for i in range(cluster.GetControlPointIndicesCount()):
                vi = indices[i]
                w = weights[i]
                if w > 0:
                    smplh_weights[vi, smplh_idx] += w
        else:
            unmapped_bones.add(bone_name)

    print(f"Mapped {mapped_count} bone clusters to SMPL-H joints")
    if unmapped_bones:
        print(f"Unmapped bones: {unmapped_bones}")

    # Normalize weights so they sum to 1 per vertex
    weight_sums = smplh_weights.sum(axis=1, keepdims=True)
    weight_sums = np.where(weight_sums > 0, weight_sums, 1.0)
    smplh_weights = smplh_weights / weight_sums

    return smplh_weights


def get_top_4_weights(full_weights):
    """
    Convert full weight matrix to top-4 weights per vertex.
    Returns (skin_indices, skin_weights) arrays.
    """
    num_verts = full_weights.shape[0]
    skin_indices = np.zeros((num_verts, 4), dtype=np.uint16)
    skin_weights = np.zeros((num_verts, 4), dtype=np.float32)

    for vi in range(num_verts):
        weights = full_weights[vi]
        # Get indices of top 4 weights
        top_indices = np.argsort(weights)[-4:][::-1]
        top_weights = weights[top_indices]

        # Normalize top 4 to sum to 1
        total = top_weights.sum()
        if total > 0:
            top_weights = top_weights / total

        skin_indices[vi] = top_indices
        skin_weights[vi] = top_weights

    return skin_indices, skin_weights


def extract_joint_positions(scene, lod1_to_smplh_idx):
    """Extract SMPL-H joint positions from lod1 skeleton."""
    j_template = np.zeros((52, 3), dtype=np.float32)

    all_nodes = collect_nodes(scene.GetRootNode())

    for lod1_name, smplh_idx in lod1_to_smplh_idx.items():
        if lod1_name not in all_nodes:
            continue

        node = all_nodes[lod1_name]
        transform = node.EvaluateGlobalTransform()
        translation = transform.GetT()

        # Only update if this is the primary bone for this joint
        # (avoid overwriting with secondary bones like twist bones)
        smplh_name = SMPLH_JOINTS[smplh_idx]
        primary_bone = {v: k for k, v in LOD1_TO_SMPLH.items() if SMPLH_JOINTS.index(v) == smplh_idx}

        # Use the first matching bone (the primary one in the mapping order)
        if lod1_name == next(iter(primary_bone.values()), None):
            j_template[smplh_idx] = [
                translation[0] / 100.0,
                translation[1] / 100.0,
                translation[2] / 100.0,
            ]

    return j_template


def main():
    input_path = str(PROJECT_ROOT / "assets" / "lod1.fbx")
    output_dir = str(PROJECT_ROOT / "scripts" / "gradio" / "static" / "assets" / "dump_lod1")

    print(f"Loading: {input_path}")

    # Create mapping from lod1 bone names to SMPL-H indices
    lod1_to_smplh_idx = {}
    for lod1_name, smplh_name in LOD1_TO_SMPLH.items():
        if smplh_name in SMPLH_JOINTS:
            lod1_to_smplh_idx[lod1_name] = SMPLH_JOINTS.index(smplh_name)

    # Load FBX
    manager, scene = FbxCommon.InitializeSdkObjects()
    result = FbxCommon.LoadScene(manager, scene, input_path)

    if not result:
        print("Failed to load FBX")
        return 1

    # Find mesh
    mesh_node = find_mesh_node(scene.GetRootNode())
    if not mesh_node:
        print("No mesh found")
        manager.Destroy()
        return 1

    mesh = mesh_node.GetNodeAttribute()
    print(f"Mesh: {mesh_node.GetName()}, {mesh.GetControlPointsCount()} vertices")

    # Extract vertices
    num_verts = mesh.GetControlPointsCount()
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
            faces.append([
                mesh.GetPolygonVertex(i, 0),
                mesh.GetPolygonVertex(i, 1),
                mesh.GetPolygonVertex(i, 2),
            ])
            faces.append([
                mesh.GetPolygonVertex(i, 0),
                mesh.GetPolygonVertex(i, 2),
                mesh.GetPolygonVertex(i, 3),
            ])
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

    # Extract simplified skin data
    print("Extracting and simplifying skin weights...")
    full_weights = extract_simplified_skin_data(mesh_node, lod1_to_smplh_idx)
    skin_indices, skin_weights = get_top_4_weights(full_weights)

    # Verify weights
    weight_sums = skin_weights.sum(axis=1)
    zero_count = np.sum(weight_sums == 0)
    print(f"Vertices with zero weights: {zero_count}")
    print(f"Weight sum range: [{weight_sums.min():.4f}, {weight_sums.max():.4f}]")

    # Extract joint positions
    print("Extracting joint positions...")
    j_template = extract_joint_positions(scene, lod1_to_smplh_idx)

    # Save data
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "v_template.bin"), "wb") as f:
        f.write(vertices.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "faces.bin"), "wb") as f:
        f.write(faces.flatten().astype(np.uint16).tobytes())

    with open(os.path.join(output_dir, "uvs.bin"), "wb") as f:
        f.write(uvs.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "skinWeights.bin"), "wb") as f:
        f.write(skin_weights.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "skinIndice.bin"), "wb") as f:
        f.write(skin_indices.flatten().astype(np.uint16).tobytes())

    with open(os.path.join(output_dir, "j_template.bin"), "wb") as f:
        f.write(j_template.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "keypoints.bin"), "wb") as f:
        f.write(j_template.flatten().astype(np.float32).tobytes())

    with open(os.path.join(output_dir, "kintree.bin"), "wb") as f:
        f.write(np.array(SMPLH_KINTREE, dtype=np.int32).tobytes())

    import json
    with open(os.path.join(output_dir, "joint_names.json"), "w") as f:
        json.dump(SMPLH_JOINTS, f, indent=2)

    print(f"\nSaved to {output_dir}")
    print(f"  Vertices: {vertices.shape}")
    print(f"  Faces: {faces.shape}")
    print(f"  Skin weights: {skin_weights.shape}")
    print(f"  Joint template: {j_template.shape}")

    manager.Destroy()
    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

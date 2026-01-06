#!/usr/bin/env python3
"""
Dump lod1.fbx mesh data to binary format for use in visualization.

This script extracts mesh data from the MHR lod1.fbx model and saves it
in the same binary format as dump_wooden, allowing it to be used with
the WoodenMesh class for web visualization.

Usage:
    python scripts/dump_lod1_mesh.py
    python scripts/dump_lod1_mesh.py --output ./scripts/gradio/static/assets/dump_mhr
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import fbx
    FBX_AVAILABLE = True
except ImportError:
    FBX_AVAILABLE = False
    print("FBX SDK not available")

# lod1.fbx to SMPL-H joint name mapping
# Maps lod1.fbx bone names to their closest SMPL-H equivalent
LOD1_TO_SMPLH_MAPPING = {
    # Main body joints
    "root": "Pelvis",
    "l_upleg": "L_Hip",
    "r_upleg": "R_Hip",
    "c_spine0": "Spine1",
    "l_lowleg": "L_Knee",
    "r_lowleg": "R_Knee",
    "c_spine1": "Spine2",
    "c_spine2": "Spine2",  # Additional spine bone -> Spine2
    "l_foot": "L_Ankle",
    "r_foot": "R_Ankle",
    "c_spine3": "Spine3",
    "l_ball": "L_Foot",
    "r_ball": "R_Foot",
    "c_neck": "Neck",
    "l_clavicle": "L_Collar",
    "r_clavicle": "R_Collar",
    "c_head": "Head",
    "c_jaw": "Head",  # Jaw -> Head
    "l_uparm": "L_Shoulder",
    "r_uparm": "R_Shoulder",
    "l_lowarm": "L_Elbow",
    "r_lowarm": "R_Elbow",
    "l_wrist": "L_Wrist",
    "r_wrist": "R_Wrist",
    # Wrist twist bones
    "l_wrist_twist": "L_Wrist",
    "r_wrist_twist": "R_Wrist",
    # Foot bones (transversetarsal, talocrural, subtalar)
    "l_transversetarsal": "L_Foot",
    "r_transversetarsal": "R_Foot",
    "l_talocrural": "L_Ankle",
    "r_talocrural": "R_Ankle",
    "l_subtalar": "L_Ankle",
    "r_subtalar": "R_Ankle",
    # Upper leg twist bones -> L_Hip/R_Hip
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
    # Lower leg twist bones -> L_Knee/R_Knee
    "l_lowleg_twist1_proc": "L_Knee",
    "l_lowleg_twist2_proc": "L_Knee",
    "l_lowleg_twist3_proc": "L_Knee",
    "l_lowleg_twist4_proc": "L_Knee",
    "r_lowleg_twist1_proc": "R_Knee",
    "r_lowleg_twist2_proc": "R_Knee",
    "r_lowleg_twist3_proc": "R_Knee",
    "r_lowleg_twist4_proc": "R_Knee",
    # Upper arm twist bones -> L_Shoulder/R_Shoulder
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
    # Lower arm twist bones -> L_Elbow/R_Elbow
    "l_lowarm_twist1_proc": "L_Elbow",
    "l_lowarm_twist2_proc": "L_Elbow",
    "l_lowarm_twist3_proc": "L_Elbow",
    "l_lowarm_twist4_proc": "L_Elbow",
    "r_lowarm_twist1_proc": "R_Elbow",
    "r_lowarm_twist2_proc": "R_Elbow",
    "r_lowarm_twist3_proc": "R_Elbow",
    "r_lowarm_twist4_proc": "R_Elbow",
    # Neck twist bones
    "c_neck_twist0_proc": "Neck",
    "c_neck_twist1_proc": "Neck",
    # Fingers
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
    "l_pinky0": "L_Pinky1",  # pinky0 is metacarpal, map to pinky1
    "l_pinky1": "L_Pinky1",
    "l_pinky2": "L_Pinky2",
    "l_pinky3": "L_Pinky3",
    "l_pinky_null": "L_Pinky3",
    "l_thumb0": "L_Thumb1",  # thumb0 is metacarpal
    "l_thumb1": "L_Thumb1",
    "l_thumb2": "L_Thumb2",
    "l_thumb3": "L_Thumb3",
    "l_thumb_null": "L_Thumb3",
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

# For backwards compatibility
MHR_TO_SMPLH_MAPPING = LOD1_TO_SMPLH_MAPPING

# For simplified FBX that already has SMPL-H names
SMPLH_IDENTITY_MAPPING = {name: name for name in [
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
]}

# Expected SMPL-H joint order (52 joints)
SMPLH_JOINT_ORDER = [
    "Pelvis", "L_Hip", "R_Hip", "Spine1", "L_Knee", "R_Knee", "Spine2",
    "L_Ankle", "R_Ankle", "Spine3", "L_Foot", "R_Foot", "Neck",
    "L_Collar", "R_Collar", "Head", "L_Shoulder", "R_Shoulder",
    "L_Elbow", "R_Elbow", "L_Wrist", "R_Wrist",
    # Left hand
    "L_Index1", "L_Index2", "L_Index3", "L_Middle1", "L_Middle2", "L_Middle3",
    "L_Pinky1", "L_Pinky2", "L_Pinky3", "L_Ring1", "L_Ring2", "L_Ring3",
    "L_Thumb1", "L_Thumb2", "L_Thumb3",
    # Right hand
    "R_Index1", "R_Index2", "R_Index3", "R_Middle1", "R_Middle2", "R_Middle3",
    "R_Pinky1", "R_Pinky2", "R_Pinky3", "R_Ring1", "R_Ring2", "R_Ring3",
    "R_Thumb1", "R_Thumb2", "R_Thumb3",
]

# SMPL-H kintree (parent indices)
SMPLH_KINTREE = [
    -1,  # 0: Pelvis (root)
    0,   # 1: L_Hip -> Pelvis
    0,   # 2: R_Hip -> Pelvis
    0,   # 3: Spine1 -> Pelvis
    1,   # 4: L_Knee -> L_Hip
    2,   # 5: R_Knee -> R_Hip
    3,   # 6: Spine2 -> Spine1
    4,   # 7: L_Ankle -> L_Knee
    5,   # 8: R_Ankle -> R_Knee
    6,   # 9: Spine3 -> Spine2
    7,   # 10: L_Foot -> L_Ankle
    8,   # 11: R_Foot -> R_Ankle
    9,   # 12: Neck -> Spine3
    9,   # 13: L_Collar -> Spine3
    9,   # 14: R_Collar -> Spine3
    12,  # 15: Head -> Neck
    13,  # 16: L_Shoulder -> L_Collar
    14,  # 17: R_Shoulder -> R_Collar
    16,  # 18: L_Elbow -> L_Shoulder
    17,  # 19: R_Elbow -> R_Shoulder
    18,  # 20: L_Wrist -> L_Elbow
    19,  # 21: R_Wrist -> R_Elbow
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


def load_fbx_scene(filepath):
    """Load FBX file and return scene."""
    fbx_manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(fbx_manager, fbx.IOSROOT)
    fbx_manager.SetIOSettings(ios)

    importer = fbx.FbxImporter.Create(fbx_manager, "")
    if not importer.Initialize(filepath, -1, fbx_manager.GetIOSettings()):
        raise Exception(f"Failed to initialize FBX importer for: {filepath}")

    scene = fbx.FbxScene.Create(fbx_manager, "")
    importer.Import(scene)
    importer.Destroy()

    return fbx_manager, scene


def collect_nodes(node, nodes_dict=None):
    """Recursively collect all nodes in the scene."""
    if nodes_dict is None:
        nodes_dict = {}
    nodes_dict[node.GetName()] = node
    for i in range(node.GetChildCount()):
        collect_nodes(node.GetChild(i), nodes_dict)
    return nodes_dict


def get_mesh_node(scene):
    """Find the mesh node in the scene."""
    root = scene.GetRootNode()

    def find_mesh(node):
        attr = node.GetNodeAttribute()
        if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.EType.eMesh:
            return node
        for i in range(node.GetChildCount()):
            result = find_mesh(node.GetChild(i))
            if result:
                return result
        return None

    return find_mesh(root)


def get_skeleton_nodes(scene):
    """Collect all skeleton nodes."""
    root = scene.GetRootNode()
    skeleton_nodes = {}

    def collect_skeleton(node):
        attr = node.GetNodeAttribute()
        if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.EType.eSkeleton:
            skeleton_nodes[node.GetName()] = node
        for i in range(node.GetChildCount()):
            collect_skeleton(node.GetChild(i))

    collect_skeleton(root)
    return skeleton_nodes


def extract_mesh_data(mesh_node):
    """Extract vertices, faces, and UVs from mesh node."""
    mesh = mesh_node.GetNodeAttribute()

    # Get mesh node's global transform
    global_transform = mesh_node.EvaluateGlobalTransform()

    # Get vertices and transform them to world space
    control_points = mesh.GetControlPoints()
    num_verts = mesh.GetControlPointsCount()
    vertices = np.zeros((num_verts, 3), dtype=np.float32)
    for i in range(num_verts):
        cp = control_points[i]
        # Transform vertex by mesh node's global transform
        transformed = global_transform.MultT(fbx.FbxVector4(cp[0], cp[1], cp[2], 1.0))
        vertices[i] = [transformed[0], transformed[1], transformed[2]]

    # Scale from cm to m (FBX typically uses cm)
    vertices = vertices / 100.0

    # Get faces
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
            # Triangulate quads
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

    # Get UVs
    uv_element = mesh.GetElementUV(0) if mesh.GetElementUVCount() > 0 else None
    uvs = np.zeros((num_verts, 2), dtype=np.float32)
    if uv_element:
        direct_array = uv_element.GetDirectArray()
        index_array = uv_element.GetIndexArray()
        mapping_mode = uv_element.GetMappingMode()
        reference_mode = uv_element.GetReferenceMode()

        if mapping_mode == fbx.FbxLayerElement.EMappingMode.eByControlPoint:
            for i in range(num_verts):
                if reference_mode == fbx.FbxLayerElement.EReferenceMode.eDirect:
                    uv = direct_array.GetAt(i)
                else:
                    idx = index_array.GetAt(i)
                    uv = direct_array.GetAt(idx)
                uvs[i] = [uv[0], uv[1]]

    return vertices, faces, uvs


def extract_skin_data(mesh_node, skeleton_nodes, joint_order, joint_mapping=None):
    """Extract skinning weights and indices."""
    if joint_mapping is None:
        joint_mapping = MHR_TO_SMPLH_MAPPING

    mesh = mesh_node.GetNodeAttribute()
    num_verts = mesh.GetControlPointsCount()

    # Initialize with 4 weights per vertex
    skin_weights = np.zeros((num_verts, 4), dtype=np.float32)
    skin_indices = np.zeros((num_verts, 4), dtype=np.uint16)

    # Get skin deformer
    skin_count = mesh.GetDeformerCount(fbx.FbxDeformer.EDeformerType.eSkin)
    if skin_count == 0:
        print("Warning: No skin deformer found")
        return skin_weights, skin_indices

    skin = mesh.GetDeformer(0, fbx.FbxDeformer.EDeformerType.eSkin)

    # Create mapping from joint names to SMPL-H indices
    name_to_smplh_idx = {}
    for src_name, smplh_name in joint_mapping.items():
        if smplh_name in joint_order:
            name_to_smplh_idx[src_name] = joint_order.index(smplh_name)

    # Collect all weights for each vertex
    vertex_weights = {i: [] for i in range(num_verts)}

    cluster_count = skin.GetClusterCount()
    for c in range(cluster_count):
        cluster = skin.GetCluster(c)
        link_node = cluster.GetLink()
        if not link_node:
            continue

        joint_name = link_node.GetName()
        if joint_name not in name_to_smplh_idx:
            # Try to find a match
            smplh_name = joint_mapping.get(joint_name)
            if smplh_name and smplh_name in joint_order:
                joint_idx = joint_order.index(smplh_name)
            else:
                continue
        else:
            joint_idx = name_to_smplh_idx[joint_name]

        indices = cluster.GetControlPointIndices()
        weights = cluster.GetControlPointWeights()

        for i in range(cluster.GetControlPointIndicesCount()):
            vi = indices[i]
            w = weights[i]
            if w > 0:
                vertex_weights[vi].append((joint_idx, w))

    # Sort weights and take top 4
    for vi in range(num_verts):
        weights = vertex_weights[vi]
        weights.sort(key=lambda x: -x[1])  # Sort by weight descending
        weights = weights[:4]  # Take top 4

        # Normalize weights
        total = sum(w for _, w in weights)
        if total > 0:
            for i, (joint_idx, w) in enumerate(weights):
                skin_indices[vi, i] = joint_idx
                skin_weights[vi, i] = w / total

    return skin_weights, skin_indices


def extract_joint_positions(skeleton_nodes, joint_order, joint_mapping=None):
    """Extract joint positions in T-pose."""
    if joint_mapping is None:
        joint_mapping = MHR_TO_SMPLH_MAPPING

    j_template = np.zeros((len(joint_order), 3), dtype=np.float32)

    for src_name, smplh_name in joint_mapping.items():
        if smplh_name not in joint_order:
            continue
        if src_name not in skeleton_nodes:
            continue

        joint_idx = joint_order.index(smplh_name)
        node = skeleton_nodes[src_name]

        # Get global transform
        transform = node.EvaluateGlobalTransform()
        translation = transform.GetT()

        # Convert from cm to m
        j_template[joint_idx] = [
            translation[0] / 100.0,
            translation[1] / 100.0,
            translation[2] / 100.0,
        ]

    return j_template


def dump_mesh_data(output_dir, vertices, faces, uvs, skin_weights, skin_indices,
                   j_template, joint_names, kintree):
    """Save all mesh data to binary files."""
    os.makedirs(output_dir, exist_ok=True)

    # v_template.bin
    with open(os.path.join(output_dir, "v_template.bin"), "wb") as f:
        f.write(vertices.flatten().astype(np.float32).tobytes())

    # faces.bin
    with open(os.path.join(output_dir, "faces.bin"), "wb") as f:
        f.write(faces.flatten().astype(np.uint16).tobytes())

    # uvs.bin
    with open(os.path.join(output_dir, "uvs.bin"), "wb") as f:
        f.write(uvs.flatten().astype(np.float32).tobytes())

    # skinWeights.bin
    with open(os.path.join(output_dir, "skinWeights.bin"), "wb") as f:
        f.write(skin_weights.flatten().astype(np.float32).tobytes())

    # skinIndice.bin
    with open(os.path.join(output_dir, "skinIndice.bin"), "wb") as f:
        f.write(skin_indices.flatten().astype(np.uint16).tobytes())

    # j_template.bin
    with open(os.path.join(output_dir, "j_template.bin"), "wb") as f:
        f.write(j_template.flatten().astype(np.float32).tobytes())

    # keypoints.bin (same as j_template for compatibility)
    with open(os.path.join(output_dir, "keypoints.bin"), "wb") as f:
        f.write(j_template.flatten().astype(np.float32).tobytes())

    # kintree.bin
    with open(os.path.join(output_dir, "kintree.bin"), "wb") as f:
        f.write(np.array(kintree, dtype=np.int32).tobytes())

    # joint_names.json
    with open(os.path.join(output_dir, "joint_names.json"), "w") as f:
        json.dump(joint_names, f, indent=2)

    print(f"Saved mesh data to {output_dir}")
    print(f"  Vertices: {vertices.shape}")
    print(f"  Faces: {faces.shape}")
    print(f"  UVs: {uvs.shape}")
    print(f"  Skin weights: {skin_weights.shape}")
    print(f"  Skin indices: {skin_indices.shape}")
    print(f"  Joint template: {j_template.shape}")
    print(f"  Kintree: {len(kintree)}")


def main():
    parser = argparse.ArgumentParser(description="Dump lod1.fbx mesh data to binary format")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="./assets/lod1_simplified.fbx",
        help="Path to lod1_simplified.fbx file (simplified skeleton with SMPL-H joint names)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./scripts/gradio/static/assets/dump_mhr",
        help="Output directory for binary files"
    )
    args = parser.parse_args()

    if not FBX_AVAILABLE:
        print("Error: FBX SDK is required to run this script")
        return 1

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1

    print(f"Loading FBX file: {args.input}")
    fbx_manager, scene = load_fbx_scene(args.input)

    try:
        # Get mesh node
        mesh_node = get_mesh_node(scene)
        if not mesh_node:
            print("Error: No mesh found in FBX file")
            return 1
        print(f"Found mesh node: {mesh_node.GetName()}")

        # Get skeleton nodes
        skeleton_nodes = get_skeleton_nodes(scene)
        print(f"Found {len(skeleton_nodes)} skeleton nodes")

        # Determine if we're using simplified FBX (has SMPL-H names directly)
        # or original lod1.fbx (needs mapping)
        has_smplh_names = any(name in SMPLH_IDENTITY_MAPPING for name in skeleton_nodes.keys())
        if has_smplh_names:
            print("Detected SMPL-H joint names - using identity mapping")
            joint_mapping = SMPLH_IDENTITY_MAPPING
        else:
            print("Using lod1 to SMPL-H mapping")
            joint_mapping = LOD1_TO_SMPLH_MAPPING

        # Extract mesh data
        print("Extracting mesh data...")
        vertices, faces, uvs = extract_mesh_data(mesh_node)

        # Extract skin data
        print("Extracting skin data...")
        skin_weights, skin_indices = extract_skin_data(mesh_node, skeleton_nodes, SMPLH_JOINT_ORDER, joint_mapping)

        # Extract joint positions
        print("Extracting joint positions...")
        j_template = extract_joint_positions(skeleton_nodes, SMPLH_JOINT_ORDER, joint_mapping)

        # Save data
        dump_mesh_data(
            args.output,
            vertices, faces, uvs,
            skin_weights, skin_indices,
            j_template, SMPLH_JOINT_ORDER, SMPLH_KINTREE
        )

        print("\nDone!")
        return 0

    finally:
        fbx_manager.Destroy()


if __name__ == "__main__":
    exit(main())

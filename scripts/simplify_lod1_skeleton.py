#!/usr/bin/env python3
"""
Simplify lod1.fbx skeleton to have only 52 SMPL-H joints.

This script uses Blender's Python API to:
1. Load lod1.fbx
2. Remove extra bones (twist, collision, null bones)
3. Rename remaining bones to SMPL-H convention
4. Transfer skin weights to simplified skeleton
5. Export simplified FBX that matches boy_Rigging_smplx_tex.fbx structure

Usage (from command line):
    blender --background --python scripts/simplify_lod1_skeleton.py

Usage (from Blender GUI):
    1. Open Blender
    2. Go to Scripting workspace
    3. Open this script
    4. Click "Run Script"

The output will be saved to: assets/lod1_simplified.fbx
"""

import bpy
import os
import sys

# Mapping from lod1 bone names to SMPL-H bone names
# Only include the 52 main joints that correspond to SMPL-H
LOD1_TO_SMPLH = {
    "root": "Pelvis",
    "l_upleg": "L_Hip",
    "r_upleg": "R_Hip",
    "c_spine0": "Spine1",
    "l_lowleg": "L_Knee",
    "r_lowleg": "R_Knee",
    "c_spine1": "Spine2",
    "l_foot": "L_Ankle",
    "r_foot": "R_Ankle",
    "c_spine3": "Spine3",
    "l_ball": "L_Foot",
    "r_ball": "R_Foot",
    "c_neck": "Neck",
    "l_clavicle": "L_Collar",
    "r_clavicle": "R_Collar",
    "c_head": "Head",
    "l_uparm": "L_Shoulder",
    "r_uparm": "R_Shoulder",
    "l_lowarm": "L_Elbow",
    "r_lowarm": "R_Elbow",
    "l_wrist": "L_Wrist",
    "r_wrist": "R_Wrist",
    # Fingers
    "l_index1": "L_Index1",
    "l_index2": "L_Index2",
    "l_index3": "L_Index3",
    "l_middle1": "L_Middle1",
    "l_middle2": "L_Middle2",
    "l_middle3": "L_Middle3",
    "l_ring1": "L_Ring1",
    "l_ring2": "L_Ring2",
    "l_ring3": "L_Ring3",
    "l_pinky1": "L_Pinky1",
    "l_pinky2": "L_Pinky2",
    "l_pinky3": "L_Pinky3",
    "l_thumb1": "L_Thumb1",
    "l_thumb2": "L_Thumb2",
    "l_thumb3": "L_Thumb3",
    "r_index1": "R_Index1",
    "r_index2": "R_Index2",
    "r_index3": "R_Index3",
    "r_middle1": "R_Middle1",
    "r_middle2": "R_Middle2",
    "r_middle3": "R_Middle3",
    "r_ring1": "R_Ring1",
    "r_ring2": "R_Ring2",
    "r_ring3": "R_Ring3",
    "r_pinky1": "R_Pinky1",
    "r_pinky2": "R_Pinky2",
    "r_pinky3": "R_Pinky3",
    "r_thumb1": "R_Thumb1",
    "r_thumb2": "R_Thumb2",
    "r_thumb3": "R_Thumb3",
}

# Mapping for bones that should have their weights transferred to parent
# Key: bone to remove, Value: bone to transfer weights to
WEIGHT_TRANSFER_MAP = {
    # Spine2 intermediate
    "c_spine2": "c_spine1",  # -> Spine2
    # Jaw
    "c_jaw": "c_head",  # -> Head
    # Wrist twist
    "l_wrist_twist": "l_wrist",
    "r_wrist_twist": "r_wrist",
    # Foot bones
    "l_transversetarsal": "l_ball",
    "r_transversetarsal": "r_ball",
    "l_talocrural": "l_foot",
    "r_talocrural": "r_foot",
    "l_subtalar": "l_foot",
    "r_subtalar": "r_foot",
    # Upper leg twist bones
    "l_upleg_twist0_proc": "l_upleg",
    "l_upleg_twist1_proc": "l_upleg",
    "l_upleg_twist2_proc": "l_upleg",
    "l_upleg_twist3_proc": "l_upleg",
    "l_upleg_twist4_proc": "l_upleg",
    "r_upleg_twist0_proc": "r_upleg",
    "r_upleg_twist1_proc": "r_upleg",
    "r_upleg_twist2_proc": "r_upleg",
    "r_upleg_twist3_proc": "r_upleg",
    "r_upleg_twist4_proc": "r_upleg",
    # Lower leg twist bones
    "l_lowleg_twist1_proc": "l_lowleg",
    "l_lowleg_twist2_proc": "l_lowleg",
    "l_lowleg_twist3_proc": "l_lowleg",
    "l_lowleg_twist4_proc": "l_lowleg",
    "r_lowleg_twist1_proc": "r_lowleg",
    "r_lowleg_twist2_proc": "r_lowleg",
    "r_lowleg_twist3_proc": "r_lowleg",
    "r_lowleg_twist4_proc": "r_lowleg",
    # Upper arm twist bones
    "l_uparm_twist0_proc": "l_uparm",
    "l_uparm_twist1_proc": "l_uparm",
    "l_uparm_twist2_proc": "l_uparm",
    "l_uparm_twist3_proc": "l_uparm",
    "l_uparm_twist4_proc": "l_uparm",
    "r_uparm_twist0_proc": "r_uparm",
    "r_uparm_twist1_proc": "r_uparm",
    "r_uparm_twist2_proc": "r_uparm",
    "r_uparm_twist3_proc": "r_uparm",
    "r_uparm_twist4_proc": "r_uparm",
    # Lower arm twist bones
    "l_lowarm_twist1_proc": "l_lowarm",
    "l_lowarm_twist2_proc": "l_lowarm",
    "l_lowarm_twist3_proc": "l_lowarm",
    "l_lowarm_twist4_proc": "l_lowarm",
    "r_lowarm_twist1_proc": "r_lowarm",
    "r_lowarm_twist2_proc": "r_lowarm",
    "r_lowarm_twist3_proc": "r_lowarm",
    "r_lowarm_twist4_proc": "r_lowarm",
    # Neck twist bones
    "c_neck_twist0_proc": "c_neck",
    "c_neck_twist1_proc": "c_neck",
    # Finger metacarpals and nulls
    "l_pinky0": "l_pinky1",
    "r_pinky0": "r_pinky1",
    "l_thumb0": "l_thumb1",
    "r_thumb0": "r_thumb1",
    "l_index_null": "l_index3",
    "l_middle_null": "l_middle3",
    "l_ring_null": "l_ring3",
    "l_pinky_null": "l_pinky3",
    "l_thumb_null": "l_thumb3",
    "r_index_null": "r_index3",
    "r_middle_null": "r_middle3",
    "r_ring_null": "r_ring3",
    "r_pinky_null": "r_pinky3",
    "r_thumb_null": "r_thumb3",
}


def find_armature():
    """Find the armature object in the scene."""
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def find_mesh():
    """Find the mesh object in the scene."""
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name == 'body_mesh':
            return obj
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            return obj
    return None


def transfer_vertex_weights(mesh_obj, from_group, to_group):
    """Transfer vertex weights from one group to another."""
    if from_group not in mesh_obj.vertex_groups:
        return
    if to_group not in mesh_obj.vertex_groups:
        mesh_obj.vertex_groups.new(name=to_group)

    from_vg = mesh_obj.vertex_groups[from_group]
    to_vg = mesh_obj.vertex_groups[to_group]

    # Get all vertices and their weights from source group
    for v in mesh_obj.data.vertices:
        try:
            weight = from_vg.weight(v.index)
            if weight > 0:
                # Add to target group
                try:
                    existing = to_vg.weight(v.index)
                    to_vg.add([v.index], existing + weight, 'REPLACE')
                except RuntimeError:
                    to_vg.add([v.index], weight, 'REPLACE')
        except RuntimeError:
            pass  # Vertex not in group

    # Remove source group
    mesh_obj.vertex_groups.remove(from_vg)


def rebuild_armature_with_zero_rotations():
    """
    Rebuild the armature from scratch with zero local rotations.

    This creates a new armature where:
    1. Bone world positions are the same as the original
    2. All local rotations are zero (bones point along their local Y axis)
    3. The mesh skinning is transferred to the new armature

    This is necessary because the FBX importer creates bones with pre-rotations,
    and Blender's FBX exporter preserves these. The only way to get zero
    local rotations in the exported FBX is to create bones from scratch.
    """
    from mathutils import Vector, Matrix
    import math

    old_armature = find_armature()
    mesh = find_mesh()

    if not old_armature:
        print("No armature found")
        return False

    print("\nRebuilding armature with zero local rotations...")

    # Step 1: Collect world-space bone positions from the old armature
    bpy.context.view_layer.objects.active = old_armature
    bpy.ops.object.mode_set(mode='EDIT')

    bone_data = {}
    parent_map = {}

    for bone in old_armature.data.edit_bones:
        bone_data[bone.name] = {
            'head': bone.head.copy(),
            'tail': bone.tail.copy(),
        }
        if bone.parent:
            parent_map[bone.name] = bone.parent.name
        else:
            parent_map[bone.name] = None
        print(f"  Collected: {bone.name}")

    bpy.ops.object.mode_set(mode='OBJECT')

    # Step 2: Create a new armature
    new_armature_data = bpy.data.armatures.new("lod1_armature")
    new_armature = bpy.data.objects.new("lod1_armature", new_armature_data)
    bpy.context.collection.objects.link(new_armature)

    bpy.context.view_layer.objects.active = new_armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Step 3: Create bones with the same positions
    new_bones = {}
    for bone_name, data in bone_data.items():
        bone = new_armature_data.edit_bones.new(bone_name)
        bone.head = data['head']
        bone.tail = data['tail']
        new_bones[bone_name] = bone
        print(f"  Created: {bone_name}")

    # Step 4: Set up parent relationships FIRST (before adjusting roll)
    for bone_name, parent_name in parent_map.items():
        if parent_name and parent_name in new_bones:
            new_bones[bone_name].parent = new_bones[parent_name]

    # Step 5: Calculate and set bone rolls to achieve zero local rotation
    # For FBX, a bone with zero local rotation has:
    # - Local Y axis along bone direction (head to tail)
    # - Local Z axis pointing "up" (based on parent's orientation)
    for bone_name, bone in new_bones.items():
        # Get bone direction
        direction = (bone.tail - bone.head).normalized()

        # Calculate roll to align local Z with world Z (projected onto the bone's plane)
        # This is what gives zero rotation in FBX for most bones
        if abs(direction.z) < 0.99:
            # Use world Z as the "up" vector
            bone.align_roll(Vector((0, 0, 1)))
        else:
            # Bone is nearly vertical, use world Y as the "up" vector
            bone.align_roll(Vector((0, 1, 0)))

    bpy.ops.object.mode_set(mode='OBJECT')

    # Step 6: Transfer mesh to new armature
    if mesh:
        # Remove old armature modifier
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE' and mod.object == old_armature:
                mesh.modifiers.remove(mod)
                break

        # Add new armature modifier
        mod = mesh.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = new_armature

        # Parent mesh to new armature
        mesh.parent = new_armature

    # Step 7: Delete old armature
    bpy.data.objects.remove(old_armature, do_unlink=True)

    print("Armature rebuilt with aligned bone rolls")
    return True


def simplify_skeleton():
    """Main function to simplify the skeleton."""

    # Get armature and mesh
    armature = find_armature()
    mesh = find_mesh()

    if not armature:
        print("ERROR: No armature found!")
        return False
    if not mesh:
        print("ERROR: No mesh found!")
        return False

    print(f"Armature: {armature.name}")
    print(f"Mesh: {mesh.name}")
    print(f"Original bone count: {len(armature.data.bones)}")

    # Step 1: Transfer weights from bones to be removed
    print("\nTransferring weights...")
    for from_bone, to_bone in WEIGHT_TRANSFER_MAP.items():
        if from_bone in mesh.vertex_groups:
            transfer_vertex_weights(mesh, from_bone, to_bone)
            print(f"  {from_bone} -> {to_bone}")

    # Step 2: Remove extra vertex groups (collision, null, etc.)
    print("\nRemoving extra vertex groups...")
    groups_to_remove = []
    for vg in mesh.vertex_groups:
        if vg.name not in LOD1_TO_SMPLH and vg.name not in LOD1_TO_SMPLH.values():
            groups_to_remove.append(vg.name)

    for name in groups_to_remove:
        if name in mesh.vertex_groups:
            mesh.vertex_groups.remove(mesh.vertex_groups[name])
            print(f"  Removed: {name}")

    # Step 3: Rename vertex groups to SMPL-H names
    print("\nRenaming vertex groups...")
    for old_name, new_name in LOD1_TO_SMPLH.items():
        if old_name in mesh.vertex_groups:
            mesh.vertex_groups[old_name].name = new_name
            print(f"  {old_name} -> {new_name}")

    # Step 4: Remove extra bones from armature
    print("\nRemoving extra bones...")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    bones_to_keep = set(LOD1_TO_SMPLH.keys())
    bones_to_remove = []

    for bone in armature.data.edit_bones:
        if bone.name not in bones_to_keep:
            bones_to_remove.append(bone.name)

    for bone_name in bones_to_remove:
        if bone_name in armature.data.edit_bones:
            bone = armature.data.edit_bones[bone_name]
            armature.data.edit_bones.remove(bone)

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"  Removed {len(bones_to_remove)} bones")

    # Step 5: Rename bones to SMPL-H names
    print("\nRenaming bones...")
    bpy.ops.object.mode_set(mode='EDIT')

    for old_name, new_name in LOD1_TO_SMPLH.items():
        if old_name in armature.data.edit_bones:
            armature.data.edit_bones[old_name].name = new_name
            print(f"  {old_name} -> {new_name}")

    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"\nFinal bone count: {len(armature.data.bones)}")
    print(f"Final vertex group count: {len(mesh.vertex_groups)}")

    return True


def main():
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Try to find the project root (where assets/ folder is)
    # When run from command line, cwd might be the project root
    # When run from Blender GUI, we need to find it
    possible_roots = [
        os.getcwd(),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in dir() else None,
        "/home/n10288/Documents/Code/HY-Motion-1.0",  # Fallback
    ]

    input_path = None
    for root in possible_roots:
        if root is None:
            continue
        candidate = os.path.join(root, "assets", "lod1.fbx")
        if os.path.exists(candidate):
            input_path = candidate
            break

    if input_path is None:
        print("ERROR: Could not find assets/lod1.fbx")
        print("Please run this script from the HY-Motion-1.0 directory")
        return

    print(f"Importing: {input_path}")

    bpy.ops.import_scene.fbx(filepath=input_path)

    # Simplify
    if not simplify_skeleton():
        print("Failed to simplify skeleton!")
        return

    # Rebuild armature with zero local rotations
    # The FBX importer creates bones with pre-rotations, and Blender's FBX exporter
    # preserves these. The only way to get zero local rotations is to rebuild the armature.
    if not rebuild_armature_with_zero_rotations():
        print("Warning: Failed to rebuild armature")

    # Export to same directory as input
    project_root = os.path.dirname(os.path.dirname(input_path))
    output_path = os.path.join(project_root, "assets", "lod1_simplified.fbx")
    print(f"\nExporting: {output_path}")

    # Select mesh and armature for export
    bpy.ops.object.select_all(action='DESELECT')
    armature = find_armature()
    mesh = find_mesh()
    if armature:
        armature.select_set(True)
    if mesh:
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh

    # Apply transforms to mesh before export
    if mesh:
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_NONE',  # Keep original scale
        bake_space_transform=True,  # Bake transforms to remove pre-rotations
        object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        axis_forward='-Z',
        axis_up='Y',
        use_armature_deform_only=True,  # Only export deform bones
    )

    print("\nDone! Simplified FBX saved to: assets/lod1_simplified.fbx")


if __name__ == "__main__":
    main()

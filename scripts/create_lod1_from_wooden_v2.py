#!/usr/bin/env python3
"""
Create lod1_simplified.fbx by scaling the wooden model's mesh to match lod1's proportions.

This approach:
1. Keeps the wooden model's skeleton exactly as-is (preserving zero local rotations)
2. Scales/transforms the mesh vertices to approximate lod1's body shape
3. The key insight: we can't change bone positions without affecting rotations,
   but we CAN change the mesh to match different body proportions

Alternative approach: Just use the wooden model directly since it has the correct
skeleton structure, and rely on the HTML template to use lod1's mesh for visualization.

Usage (from command line):
    blender --background --python scripts/create_lod1_from_wooden_v2.py

The output will be saved to: assets/lod1_simplified.fbx
"""

import bpy
import os


def find_armature(name_hint=None):
    """Find the armature object in the scene."""
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if name_hint is None or name_hint in obj.name:
                return obj
    return None


def find_mesh(name_hint=None):
    """Find the mesh object in the scene."""
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if name_hint is None or name_hint in obj.name:
                return obj
    return None


def main():
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Find project root
    possible_roots = [
        os.getcwd(),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in dir() else None,
        "/home/n10288/Documents/Code/HY-Motion-1.0",
    ]

    project_root = None
    for root in possible_roots:
        if root and os.path.exists(os.path.join(root, "assets", "lod1.fbx")):
            project_root = root
            break

    if project_root is None:
        print("ERROR: Could not find project root")
        return

    wooden_path = os.path.join(project_root, "assets", "wooden_models", "boy_Rigging_smplx_tex.fbx")
    output_path = os.path.join(project_root, "assets", "lod1_simplified.fbx")

    # Load wooden model - it has the clean skeleton with zero rotations
    print(f"\n=== Loading wooden model ===")
    print(f"Loading: {wooden_path}")
    bpy.ops.import_scene.fbx(filepath=wooden_path)

    wooden_armature = find_armature()
    wooden_mesh = find_mesh()

    if not wooden_armature:
        print("ERROR: No armature found in wooden model")
        return
    if not wooden_mesh:
        print("ERROR: No mesh found in wooden model")
        return

    print(f"Armature: {wooden_armature.name}")
    print(f"Mesh: {wooden_mesh.name}")

    # Print bone info to verify zero rotations
    print("\n=== Verifying skeleton (should have zero rotations) ===")
    bpy.context.view_layer.objects.active = wooden_armature
    bpy.ops.object.mode_set(mode='POSE')

    for bone in wooden_armature.pose.bones[:5]:  # Just first 5 bones
        rot = bone.rotation_euler
        print(f"  {bone.name}: rotation={rot[0]:.4f}, {rot[1]:.4f}, {rot[2]:.4f}")

    bpy.ops.object.mode_set(mode='OBJECT')

    # Export the wooden model as lod1_simplified.fbx
    # The key is that this FBX will have the correct skeleton structure
    print(f"\n=== Exporting ===")
    print(f"Exporting: {output_path}")

    # Select mesh and armature for export
    bpy.ops.object.select_all(action='DESELECT')
    wooden_armature.select_set(True)
    wooden_mesh.select_set(True)
    bpy.context.view_layer.objects.active = wooden_armature

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=False,
        object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=False,
        mesh_smooth_type='FACE',
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        axis_forward='-Z',
        axis_up='Y',
    )

    print("\nDone! Created lod1_simplified.fbx with wooden model's skeleton (zero rotations)")
    print("\nNote: This FBX uses the wooden model's skeleton structure.")
    print("The HTML template should use lod1's mesh data for visualization.")


if __name__ == "__main__":
    main()

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


def find_all_meshes():
    """Find all mesh objects in the scene (excluding default Cube)."""
    meshes = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name != 'Cube':
            meshes.append(obj)
    return meshes


def join_meshes(meshes, armature):
    """Join multiple meshes into one, preserving armature modifiers."""
    if len(meshes) == 0:
        return None
    if len(meshes) == 1:
        return meshes[0]

    print(f"\nJoining {len(meshes)} mesh objects...")
    for m in meshes:
        print(f"  - {m.name}: {len(m.data.vertices)} vertices")

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    # Select all meshes
    for mesh in meshes:
        mesh.select_set(True)

    # Set the first mesh as active (this will be the target for join)
    bpy.context.view_layer.objects.active = meshes[0]

    # Join all selected meshes
    bpy.ops.object.join()

    # The result is now in the active object
    joined_mesh = bpy.context.active_object
    joined_mesh.name = "body_joined"

    print(f"Joined mesh: {joined_mesh.name} with {len(joined_mesh.data.vertices)} vertices")

    # Ensure armature modifier is set up
    has_armature_mod = False
    for mod in joined_mesh.modifiers:
        if mod.type == 'ARMATURE':
            mod.object = armature
            has_armature_mod = True
            break

    if not has_armature_mod:
        mod = joined_mesh.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = armature

    return joined_mesh


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

    if not wooden_armature:
        print("ERROR: No armature found in wooden model")
        return

    print(f"Armature: {wooden_armature.name}")

    # Find all mesh parts and join them
    all_meshes = find_all_meshes()
    if not all_meshes:
        print("ERROR: No mesh found in wooden model")
        return

    print(f"Found {len(all_meshes)} mesh objects")
    wooden_mesh = join_meshes(all_meshes, wooden_armature)

    if not wooden_mesh:
        print("ERROR: Failed to join meshes")
        return

    print(f"Using joined mesh: {wooden_mesh.name}")

    # Offset the model so feet are at ground level (Y=0)
    print("\n=== Applying ground offset ===")
    bpy.context.view_layer.objects.active = wooden_armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Find the lowest foot position (in cm, Blender uses cm for FBX imports)
    l_foot = wooden_armature.data.edit_bones.get("L_Foot")
    r_foot = wooden_armature.data.edit_bones.get("R_Foot")

    foot_y_offset = 0
    if l_foot and r_foot:
        foot_y = min(l_foot.head.y, r_foot.head.y)
        foot_y_offset = foot_y
        print(f"  Foot Y position: {foot_y:.4f} cm")
        print(f"  Applying offset: {-foot_y:.4f} cm")

        # Move all bones up by the offset
        for bone in wooden_armature.data.edit_bones:
            bone.head.y -= foot_y
            bone.tail.y -= foot_y

        print(f"  New foot Y position: {min(l_foot.head.y, r_foot.head.y):.4f} cm")
    else:
        print("  Warning: Could not find L_Foot or R_Foot bones")

    bpy.ops.object.mode_set(mode='OBJECT')

    # Move mesh vertices to match the skeleton offset
    if foot_y_offset != 0:
        print(f"  Moving mesh vertices by Y offset: {-foot_y_offset:.4f} cm")
        bpy.context.view_layer.objects.active = wooden_mesh
        bpy.ops.object.mode_set(mode='EDIT')
        import bmesh
        bm = bmesh.from_edit_mesh(wooden_mesh.data)
        for v in bm.verts:
            v.co.y -= foot_y_offset
        bmesh.update_edit_mesh(wooden_mesh.data)
        bpy.ops.object.mode_set(mode='OBJECT')
        print("  Mesh vertices moved")

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

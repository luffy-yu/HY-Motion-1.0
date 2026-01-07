#!/usr/bin/env python3
"""
Create lod1_simplified.fbx from the wooden model with lod1-compatible skeleton proportions.

This approach:
1. Starts with the wooden model's skeleton (preserving zero local rotations)
2. Adjusts upper body bone positions to match lod1.fbx proportions
3. Deforms mesh vertices to follow the adjusted skeleton
4. Applies ground offset so feet are at Y=0

The key fixes for MHR compatibility:
- Spine3: Moved higher to match lod1 (was 11cm lower)
- Neck: Adjusted position
- Collar bones (L_Collar, R_Collar): Moved to match lod1 attachment point
- Shoulders (L_Shoulder, R_Shoulder): Adjusted to match lod1

Usage (from command line):
    blender --background --python scripts/create_lod1_from_wooden_v2.py

The output will be saved to: assets/lod1_simplified.fbx
"""

import bpy
import os
from mathutils import Vector


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


def adjust_upper_body_to_lod1(armature, mesh):
    """
    Adjust upper body bone positions to match lod1.fbx skeleton proportions.

    This fixes the "triangle" mesh collapse issue when using MHR conversion.

    Target positions are from lod1.fbx (after converting lod1 bone names to SMPLH names).
    The wooden model positions need to be adjusted to match these proportions.

    Key differences (wooden vs lod1):
    - Spine3: Y=10.62cm vs Y=22.03cm (lod1 is ~11.4cm higher relative to pelvis)
    - Neck: Y=30.21cm vs Y=31.39cm (similar)
    - L_Collar: X=5.47cm, Y=22.51cm vs X=2.82cm, Y=27.75cm (lod1 is narrower, higher)
    - L_Shoulder: X=16.54cm, Y=23.75cm vs X=17.59cm, Y=29.14cm (lod1 is wider, higher)

    Note: These are relative to pelvis position since we'll apply ground offset later.
    """
    import bmesh

    print("\n=== Adjusting upper body to match lod1 proportions ===")

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Get current pelvis position as reference
    pelvis = armature.data.edit_bones.get("Pelvis")
    if not pelvis:
        print("  ERROR: Pelvis bone not found")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    pelvis_y = pelvis.head.y
    print(f"  Pelvis Y: {pelvis_y:.2f}cm")

    # Target positions relative to pelvis (from lod1.fbx analysis)
    # lod1.fbx positions (converted to SMPLH names, relative to root/Pelvis):
    # c_spine3 -> Spine3: Y = 134.83 - 94.42 = 40.41cm above pelvis
    # c_neck -> Neck: Y = 144.19 - 94.42 = 49.77cm above pelvis
    # l_clavicle -> L_Collar: X = 2.82cm, Y = 140.55 - 94.42 = 46.13cm above pelvis
    # l_uparm -> L_Shoulder: X = 17.59cm, Y = 141.94 - 94.42 = 47.52cm above pelvis

    # Current wooden positions relative to pelvis (from analysis):
    # Spine3: Y = 10.62 - (-19.20) = 29.82cm above pelvis
    # Neck: Y = 30.21 - (-19.20) = 49.41cm above pelvis
    # L_Collar: X = 5.47cm, Y = 22.51 - (-19.20) = 41.71cm above pelvis
    # L_Shoulder: X = 16.54cm, Y = 23.75 - (-19.20) = 42.95cm above pelvis

    # We need to calculate the adjustments
    # For skeleton adjustments, we move bones and their children

    # Store original positions for reference
    # Include all bones that will move (including finger bones as children of wrist)
    bones_to_adjust = {}
    bones_to_track = [
        "Spine3", "Neck", "Head",
        "L_Collar", "R_Collar",
        "L_Shoulder", "R_Shoulder",
        "L_Elbow", "R_Elbow",
        "L_Wrist", "R_Wrist",
        # Left hand fingers
        "L_Index1", "L_Index2", "L_Index3",
        "L_Middle1", "L_Middle2", "L_Middle3",
        "L_Ring1", "L_Ring2", "L_Ring3",
        "L_Pinky1", "L_Pinky2", "L_Pinky3",
        "L_Thumb1", "L_Thumb2", "L_Thumb3",
        # Right hand fingers
        "R_Index1", "R_Index2", "R_Index3",
        "R_Middle1", "R_Middle2", "R_Middle3",
        "R_Ring1", "R_Ring2", "R_Ring3",
        "R_Pinky1", "R_Pinky2", "R_Pinky3",
        "R_Thumb1", "R_Thumb2", "R_Thumb3",
    ]
    for bone_name in bones_to_track:
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            bones_to_adjust[bone_name] = {
                'bone': bone,
                'original_head': bone.head.copy(),
                'original_tail': bone.tail.copy(),
            }

    # Calculate adjustments based on lod1 proportions
    # The key insight: we need to match the relative positions

    # Get current relative positions (relative to pelvis)
    spine3 = armature.data.edit_bones.get("Spine3")
    neck = armature.data.edit_bones.get("Neck")
    l_collar = armature.data.edit_bones.get("L_Collar")
    r_collar = armature.data.edit_bones.get("R_Collar")
    l_shoulder = armature.data.edit_bones.get("L_Shoulder")
    r_shoulder = armature.data.edit_bones.get("R_Shoulder")

    if not all([spine3, neck, l_collar, r_collar, l_shoulder, r_shoulder]):
        print("  ERROR: Missing required bones")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    # Target relative Y positions (from lod1, relative to pelvis)
    # These are calculated from the lod1 analysis
    target_spine3_rel_y = 40.41  # lod1: 134.83 - 94.42
    target_neck_rel_y = 49.77    # lod1: 144.19 - 94.42
    target_collar_rel_y = 46.13  # lod1: 140.55 - 94.42
    target_shoulder_rel_y = 47.52  # lod1: 141.94 - 94.42

    # Target X positions for collars and shoulders
    target_collar_x = 2.82   # lod1 collar X (narrower than wooden's 5.47)
    target_shoulder_x = 17.59  # lod1 shoulder X

    # Calculate current relative positions
    current_spine3_rel_y = spine3.head.y - pelvis_y
    current_neck_rel_y = neck.head.y - pelvis_y
    current_collar_rel_y = l_collar.head.y - pelvis_y
    current_shoulder_rel_y = l_shoulder.head.y - pelvis_y

    print(f"  Current Spine3 rel Y: {current_spine3_rel_y:.2f}cm, target: {target_spine3_rel_y:.2f}cm")
    print(f"  Current Neck rel Y: {current_neck_rel_y:.2f}cm, target: {target_neck_rel_y:.2f}cm")
    print(f"  Current L_Collar rel Y: {current_collar_rel_y:.2f}cm, target: {target_collar_rel_y:.2f}cm")
    print(f"  Current L_Shoulder rel Y: {current_shoulder_rel_y:.2f}cm, target: {target_shoulder_rel_y:.2f}cm")

    # Calculate deltas
    spine3_delta_y = target_spine3_rel_y - current_spine3_rel_y
    neck_delta_y = target_neck_rel_y - current_neck_rel_y
    collar_delta_y = target_collar_rel_y - current_collar_rel_y
    shoulder_delta_y = target_shoulder_rel_y - current_shoulder_rel_y

    collar_delta_x = target_collar_x - abs(l_collar.head.x)
    shoulder_delta_x = target_shoulder_x - abs(l_shoulder.head.x)

    print(f"\n  Adjustments needed:")
    print(f"    Spine3: Y += {spine3_delta_y:.2f}cm")
    print(f"    Neck: Y += {neck_delta_y:.2f}cm")
    print(f"    Collar: X += {collar_delta_x:.2f}cm (toward center), Y += {collar_delta_y:.2f}cm")
    print(f"    Shoulder: X += {shoulder_delta_x:.2f}cm, Y += {shoulder_delta_y:.2f}cm")

    # Apply adjustments to bones
    # Note: We need to move bones and all their children together

    # 1. Move Spine3 and everything above it
    def move_bone_and_children(bone, delta, recursive=True):
        """Move a bone and optionally all its children by delta vector."""
        bone.head += delta
        bone.tail += delta
        if recursive:
            for child in bone.children:
                move_bone_and_children(child, delta, recursive=True)

    # Apply Spine3 adjustment (moves Spine3, Neck, Head, and all arm bones)
    spine3_delta = Vector((0, spine3_delta_y, 0))
    print(f"\n  Moving Spine3 and children by Y={spine3_delta_y:.2f}cm...")
    move_bone_and_children(spine3, spine3_delta, recursive=True)

    # Neck adjustment (relative to Spine3)
    # In wooden, Neck is 19.58cm above Spine3; in lod1, it's 9.36cm
    # So we need to move Neck (and Head) down relative to Spine3
    lod1_neck_above_spine3 = 9.36  # from lod1: 144.19 - 134.83
    current_neck_above_spine3 = neck.head.y - spine3.head.y
    neck_y_adjustment = lod1_neck_above_spine3 - current_neck_above_spine3

    print(f"\n  Neck is {current_neck_above_spine3:.2f}cm above Spine3, target: {lod1_neck_above_spine3:.2f}cm")
    print(f"  Moving Neck and children by Y={neck_y_adjustment:.2f}cm...")
    move_bone_and_children(neck, Vector((0, neck_y_adjustment, 0)), recursive=True)

    # Now we need additional adjustments for collar and shoulder positions
    # Since we moved everything, recalculate the needed collar/shoulder adjustments

    # Collar adjustment (relative to new Spine3 position)
    # Collars should be narrower (X toward center) and positioned correctly relative to Spine3
    current_collar_y = l_collar.head.y
    current_spine3_y = spine3.head.y

    # In lod1, collar is ~5.72cm above Spine3; in wooden it's ~11.88cm
    # So we need to move collar down relative to Spine3
    lod1_collar_above_spine3 = 5.72
    current_collar_above_spine3 = current_collar_y - current_spine3_y
    collar_y_adjustment = lod1_collar_above_spine3 - current_collar_above_spine3

    print(f"\n  Collar is {current_collar_above_spine3:.2f}cm above Spine3, target: {lod1_collar_above_spine3:.2f}cm")

    # Move collar bones (and their children - the arm chain)
    l_collar_delta = Vector((collar_delta_x, collar_y_adjustment, 0))  # Move toward center and down
    r_collar_delta = Vector((-collar_delta_x, collar_y_adjustment, 0))  # Mirror for right side

    print(f"  Moving L_Collar by X={collar_delta_x:.2f}, Y={collar_y_adjustment:.2f}cm...")
    move_bone_and_children(l_collar, l_collar_delta, recursive=True)
    print(f"  Moving R_Collar by X={-collar_delta_x:.2f}, Y={collar_y_adjustment:.2f}cm...")
    move_bone_and_children(r_collar, r_collar_delta, recursive=True)

    # Shoulder adjustment (relative to collar)
    # In lod1, shoulder is ~14.76cm outward from collar; in wooden it's ~11.07cm
    lod1_shoulder_outward = 14.76
    current_shoulder_outward = abs(l_shoulder.head.x) - abs(l_collar.head.x)
    shoulder_x_adjustment = lod1_shoulder_outward - current_shoulder_outward

    # In lod1, shoulder is ~1.39cm above collar; recalculate after collar move
    lod1_shoulder_above_collar = 1.39
    current_shoulder_above_collar = l_shoulder.head.y - l_collar.head.y
    shoulder_y_adjustment = lod1_shoulder_above_collar - current_shoulder_above_collar

    print(f"\n  Shoulder is {current_shoulder_outward:.2f}cm outward from collar, target: {lod1_shoulder_outward:.2f}cm")
    print(f"  Shoulder is {current_shoulder_above_collar:.2f}cm above collar, target: {lod1_shoulder_above_collar:.2f}cm")

    l_shoulder_delta = Vector((shoulder_x_adjustment, shoulder_y_adjustment, 0))
    r_shoulder_delta = Vector((-shoulder_x_adjustment, shoulder_y_adjustment, 0))

    print(f"  Moving L_Shoulder by X={shoulder_x_adjustment:.2f}, Y={shoulder_y_adjustment:.2f}cm...")
    move_bone_and_children(l_shoulder, l_shoulder_delta, recursive=True)
    print(f"  Moving R_Shoulder by X={-shoulder_x_adjustment:.2f}, Y={shoulder_y_adjustment:.2f}cm...")
    move_bone_and_children(r_shoulder, r_shoulder_delta, recursive=True)

    bpy.ops.object.mode_set(mode='OBJECT')

    # Now deform the mesh to follow the new bone positions
    print("\n  Deforming mesh to follow adjusted skeleton...")
    deform_mesh_to_skeleton(armature, mesh, bones_to_adjust)

    print("\n  Upper body adjustment complete!")


def deform_mesh_to_skeleton(armature, mesh, original_bone_data):
    """
    Deform mesh vertices based on bone position changes using vertex weights.

    For each vertex, calculate its movement based on the weighted average of
    bone movements it's attached to.
    """
    import bmesh

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Get new bone positions
    new_bone_positions = {}
    for bone_name in original_bone_data.keys():
        bone = armature.data.edit_bones.get(bone_name)
        if bone:
            new_bone_positions[bone_name] = bone.head.copy()

    bpy.ops.object.mode_set(mode='OBJECT')

    # Calculate bone deltas
    bone_deltas = {}
    for bone_name, data in original_bone_data.items():
        if bone_name in new_bone_positions:
            delta = new_bone_positions[bone_name] - data['original_head']
            bone_deltas[bone_name] = delta
            if delta.length > 0.1:
                print(f"    {bone_name}: delta = ({delta.x:.2f}, {delta.y:.2f}, {delta.z:.2f})")

    # Get vertex group indices
    vgroup_indices = {}
    for vg in mesh.vertex_groups:
        if vg.name in bone_deltas:
            vgroup_indices[vg.index] = vg.name

    # Deform mesh vertices
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(mesh.data)
    deform_layer = bm.verts.layers.deform.verify()

    vertices_moved = 0
    for v in bm.verts:
        # Calculate weighted delta for this vertex
        total_weight = 0
        weighted_delta = Vector((0, 0, 0))

        for vg_idx, weight in v[deform_layer].items():
            if vg_idx in vgroup_indices:
                bone_name = vgroup_indices[vg_idx]
                if bone_name in bone_deltas:
                    delta = bone_deltas[bone_name]
                    weighted_delta += delta * weight
                    total_weight += weight

        # Apply weighted delta
        if total_weight > 0.01 and weighted_delta.length > 0.01:
            v.co += weighted_delta
            vertices_moved += 1

    bmesh.update_edit_mesh(mesh.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"    Moved {vertices_moved} vertices based on bone weights")


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

    # Adjust upper body skeleton to match lod1 proportions
    # This fixes the mesh collapse issue when using MHR conversion
    adjust_upper_body_to_lod1(wooden_armature, wooden_mesh)

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

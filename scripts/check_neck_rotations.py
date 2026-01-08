#!/usr/bin/env python3
"""Check neck/chest rotations in animated FBX."""

import fbx
import numpy as np


def check_joint_rotations(filepath, joint_names):
    """Check rotation animation curves for specified joints."""
    manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ios)

    importer = fbx.FbxImporter.Create(manager, '')
    if not importer.Initialize(filepath, -1, manager.GetIOSettings()):
        print(f'Error initializing {filepath}: {importer.GetStatus().GetErrorString()}')
        manager.Destroy()
        return

    scene = fbx.FbxScene.Create(manager, 'Scene')
    importer.Import(scene)
    importer.Destroy()

    # Collect all nodes
    def collect_nodes(node, nodes):
        nodes[node.GetName()] = node
        for i in range(node.GetChildCount()):
            collect_nodes(node.GetChild(i), nodes)
        return nodes

    nodes = collect_nodes(scene.GetRootNode(), {})

    print(f'\n=== {filepath.split("/")[-1]} ===')

    # Get animation
    anim_stack = scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId), 0)
    if not anim_stack:
        print("No animation found")
        manager.Destroy()
        return

    anim_layer = anim_stack.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId), 0)
    if not anim_layer:
        print("No animation layer found")
        manager.Destroy()
        return

    for joint in joint_names:
        if joint not in nodes:
            print(f"{joint}: NOT FOUND")
            continue

        node = nodes[joint]
        local_rot = node.LclRotation.Get()
        print(f"\n{joint}:")
        print(f"  Local Rotation: X={local_rot[0]:.2f}, Y={local_rot[1]:.2f}, Z={local_rot[2]:.2f}")

        # Check animation curves
        has_anim = False
        for channel in ['X', 'Y', 'Z']:
            curve = node.LclRotation.GetCurve(anim_layer, channel)
            if curve and curve.KeyGetCount() > 0:
                has_anim = True
                key_count = curve.KeyGetCount()
                first_val = curve.KeyGetValue(0)
                last_val = curve.KeyGetValue(key_count - 1)
                min_val = min([curve.KeyGetValue(i) for i in range(key_count)])
                max_val = max([curve.KeyGetValue(i) for i in range(key_count)])
                print(f"  Rot {channel} anim: {key_count} keys, first={first_val:.2f}, last={last_val:.2f}, range=[{min_val:.2f}, {max_val:.2f}]")

        if not has_anim:
            print("  No rotation animation")

    manager.Destroy()


def main():
    joints_to_check = ['Hips', 'SpineLower', 'SpineMiddle', 'SpineUpper', 'Chest', 'Neck', 'Head']

    # Check both outputs
    check_joint_rotations(
        '/home/n10288/Documents/Code/HY-Motion-1.0/MHR/tools/mhr_smpl_conversion/output_test_with_global_orient/high_fidelity_rig_animated.fbx',
        joints_to_check
    )

    check_joint_rotations(
        '/home/n10288/Documents/Code/HY-Motion-1.0/MHR/tools/mhr_smpl_conversion/output_hf_fbx_input_test/high_fidelity_rig_animated.fbx',
        joints_to_check
    )


if __name__ == '__main__':
    main()

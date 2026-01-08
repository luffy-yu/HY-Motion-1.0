#!/usr/bin/env python3
"""Compare two animated FBX outputs to find differences."""

import fbx
import numpy as np


def analyze_fbx(filepath):
    """Analyze an FBX file and return joint info."""
    manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ios)

    importer = fbx.FbxImporter.Create(manager, '')
    if not importer.Initialize(filepath, -1, manager.GetIOSettings()):
        print(f'Error initializing {filepath}')
        manager.Destroy()
        return None

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

    # Get animation
    anim_stack = scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId), 0)
    anim_layer = None
    if anim_stack:
        anim_layer = anim_stack.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId), 0)

    results = {}
    joints = ['Hips', 'SpineLower', 'SpineMiddle', 'SpineUpper', 'Chest', 'Neck', 'Head',
              'LeftShoulder', 'RightShoulder', 'LeftArmUpper', 'RightArmUpper']

    for joint in joints:
        if joint not in nodes:
            continue

        node = nodes[joint]
        local_trans = node.LclTranslation.Get()
        local_rot = node.LclRotation.Get()

        info = {
            'local_trans_y': local_trans[1],
            'local_rot': [local_rot[0], local_rot[1], local_rot[2]],
            'has_trans_anim': False,
            'has_rot_anim': False,
            'trans_y_first': None,
            'rot_first': None,
        }

        if anim_layer:
            # Check translation Y curve
            y_curve = node.LclTranslation.GetCurve(anim_layer, 'Y')
            if y_curve and y_curve.KeyGetCount() > 0:
                info['has_trans_anim'] = True
                info['trans_y_first'] = y_curve.KeyGetValue(0)

            # Check rotation X curve (as sample)
            for ch in ['X', 'Y', 'Z']:
                curve = node.LclRotation.GetCurve(anim_layer, ch)
                if curve and curve.KeyGetCount() > 0:
                    info['has_rot_anim'] = True
                    if info['rot_first'] is None:
                        info['rot_first'] = [0, 0, 0]
                    idx = ['X', 'Y', 'Z'].index(ch)
                    info['rot_first'][idx] = curve.KeyGetValue(0)

        results[joint] = info

    manager.Destroy()
    return results


def main():
    # Working output
    working = analyze_fbx('/home/n10288/Documents/Code/HY-Motion-1.0/MHR/tools/mhr_smpl_conversion/output_simplified_hf_test_neck_no_offset/high_fidelity_rig_animated.fbx')

    # Not working output (with triangle)
    broken = analyze_fbx('/home/n10288/Documents/Code/HY-Motion-1.0/MHR/tools/mhr_smpl_conversion/output_hf_fbx_input_test/high_fidelity_rig_animated.fbx')

    if not working or not broken:
        print("Failed to load one or both files")
        return

    print("=" * 80)
    print("COMPARISON: Working vs Broken (Triangle Issue)")
    print("=" * 80)

    all_joints = set(working.keys()) | set(broken.keys())
    for joint in sorted(all_joints):
        w = working.get(joint, {})
        b = broken.get(joint, {})

        if not w and not b:
            continue

        print(f"\n{joint}:")

        # Compare local translation Y
        w_ty = w.get('local_trans_y', 'N/A')
        b_ty = b.get('local_trans_y', 'N/A')
        if w_ty != b_ty:
            print(f"  Local Trans Y: Working={w_ty:.4f} vs Broken={b_ty:.4f} [DIFF]")
        else:
            print(f"  Local Trans Y: {w_ty:.4f} [SAME]")

        # Compare trans animation
        w_ta = w.get('has_trans_anim', False)
        b_ta = b.get('has_trans_anim', False)
        if w_ta != b_ta:
            print(f"  Has Trans Anim: Working={w_ta} vs Broken={b_ta} [DIFF]")
        elif w_ta:
            w_tfy = w.get('trans_y_first')
            b_tfy = b.get('trans_y_first')
            if w_tfy is not None and b_tfy is not None and abs(w_tfy - b_tfy) > 0.01:
                print(f"  Trans Y First Key: Working={w_tfy:.4f} vs Broken={b_tfy:.4f} [DIFF]")

        # Compare rotation animation first keys
        w_rf = w.get('rot_first')
        b_rf = b.get('rot_first')
        if w_rf and b_rf:
            max_diff = max(abs(w_rf[i] - b_rf[i]) for i in range(3))
            if max_diff > 5:  # More than 5 degrees difference
                print(f"  Rot First Key: Working={w_rf} vs Broken={b_rf} [DIFF: {max_diff:.1f}°]")


if __name__ == '__main__':
    main()

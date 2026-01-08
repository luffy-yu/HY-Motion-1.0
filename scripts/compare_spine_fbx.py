#!/usr/bin/env python3
"""Compare spine chain positions between two FBX files."""

import fbx
import sys

def analyze_spine_chain(filepath):
    manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ios)

    importer = fbx.FbxImporter.Create(manager, '')
    if not importer.Initialize(filepath, -1, manager.GetIOSettings()):
        print(f'Error initializing {filepath}: {importer.GetStatus().GetErrorString()}')
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

    print(f'\n=== {filepath} ===')

    # Get spine chain joints
    spine_joints = ['Hips', 'SpineLower', 'SpineMiddle', 'SpineUpper', 'Chest', 'Neck']

    results = {}
    for joint in spine_joints:
        if joint in nodes:
            node = nodes[joint]
            local_trans = node.LclTranslation.Get()
            results[joint] = {'local_y': local_trans[1], 'anim_y': None}
            print(f'{joint:15} LocalY: {local_trans[1]:8.4f} cm')

            # Check if there's animation on this joint
            anim_stack = scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId), 0)
            if anim_stack:
                anim_layer = anim_stack.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId), 0)
                if anim_layer:
                    # Check Y translation curve
                    y_curve = node.LclTranslation.GetCurve(anim_layer, 'Y')
                    if y_curve and y_curve.KeyGetCount() > 0:
                        first_key = y_curve.KeyGetValue(0)
                        results[joint]['anim_y'] = first_key
                        print(f'                 AnimKeyY[0]: {first_key:8.4f} cm')

    manager.Destroy()
    return results


def main():
    original = '/home/n10288/Documents/Code/HY-Motion-1.0/assets/meta_movementsdk_models/high_fidelity_rig.fbx'
    animated = '/home/n10288/Documents/Code/HY-Motion-1.0/MHR/tools/mhr_smpl_conversion/output_hf_fbx_input_test/high_fidelity_rig_animated.fbx'

    result1 = analyze_spine_chain(original)
    result2 = analyze_spine_chain(animated)

    if result1 and result2:
        print('\n=== COMPARISON ===')
        for joint in ['SpineUpper', 'Chest', 'Neck']:
            if joint in result1 and joint in result2:
                orig_y = result1[joint]['local_y']
                anim_y = result2[joint].get('anim_y') or result2[joint]['local_y']
                diff = anim_y - orig_y
                print(f'{joint:15} Original: {orig_y:8.4f}, Animated: {anim_y:8.4f}, Diff: {diff:+8.4f} cm')


if __name__ == '__main__':
    main()

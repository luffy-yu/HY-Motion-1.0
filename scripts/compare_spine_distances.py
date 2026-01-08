#!/usr/bin/env python3
"""Compare spine chain bone distances between HF rig and LOD1."""

import fbx
import numpy as np


def get_world_position(node, manager):
    """Get world position of a node."""
    evaluator = node.GetScene().GetAnimationEvaluator()
    time = fbx.FbxTime()
    time.SetFrame(0)
    global_transform = evaluator.GetNodeGlobalTransform(node, time)
    translation = global_transform.GetT()
    return np.array([translation[0], translation[1], translation[2]])


def analyze_spine_distances(filepath, joint_list):
    """Analyze spine chain and compute distances between joints."""
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

    print(f'\n=== {filepath.split("/")[-1]} ===')
    print(f'{"Joint":15} {"WorldPos (cm)":30} {"Dist to Next (cm)":18}')
    print('-' * 65)

    positions = {}
    for joint in joint_list:
        if joint in nodes:
            pos = get_world_position(nodes[joint], manager)
            positions[joint] = pos
            print(f'{joint:15} [{pos[0]:8.4f}, {pos[1]:8.4f}, {pos[2]:8.4f}]')

    # Calculate distances between consecutive joints
    distances = {}
    for i in range(len(joint_list) - 1):
        j1, j2 = joint_list[i], joint_list[i + 1]
        if j1 in positions and j2 in positions:
            dist = np.linalg.norm(positions[j2] - positions[j1])
            distances[(j1, j2)] = dist
            print(f'  {j1} -> {j2}: {dist:.4f} cm')

    manager.Destroy()
    return positions, distances


def main():
    # HF rig
    hf_joints = ['Hips', 'SpineLower', 'SpineMiddle', 'SpineUpper', 'Chest', 'Neck']
    hf_result = analyze_spine_distances(
        '/home/n10288/Documents/Code/HY-Motion-1.0/assets/meta_movementsdk_models/high_fidelity_rig.fbx',
        hf_joints
    )

    # LOD1 template
    lod1_joints = ['root', 'c_spine0', 'c_spine1', 'c_spine2', 'c_spine3', 'c_neck']
    lod1_result = analyze_spine_distances(
        '/home/n10288/Documents/Code/HY-Motion-1.0/assets/lod1.fbx',
        lod1_joints
    )

    if hf_result and lod1_result:
        hf_pos, hf_dist = hf_result
        lod1_pos, lod1_dist = lod1_result

        print('\n=== DISTANCE COMPARISON ===')
        print(f'{"LOD1 Segment":25} {"Dist":8} {"HF Segment":25} {"Dist":8} {"Diff":8}')
        print('-' * 80)

        # Compare corresponding segments
        mappings = [
            (('c_spine0', 'c_spine1'), ('SpineLower', 'SpineMiddle')),
            (('c_spine1', 'c_spine2'), ('SpineMiddle', 'SpineUpper')),
            (('c_spine2', 'c_spine3'), ('SpineUpper', 'Chest')),
            (('c_spine3', 'c_neck'), ('Chest', 'Neck')),
        ]

        for lod1_seg, hf_seg in mappings:
            lod1_d = lod1_dist.get(lod1_seg, 0)
            hf_d = hf_dist.get(hf_seg, 0)
            diff = lod1_d - hf_d
            lod1_name = f'{lod1_seg[0]} -> {lod1_seg[1]}'
            hf_name = f'{hf_seg[0]} -> {hf_seg[1]}'
            print(f'{lod1_name:25} {lod1_d:8.4f} {hf_name:25} {hf_d:8.4f} {diff:+8.4f}')

        # Total distance from spine1/SpineMiddle to neck
        lod1_total = sum([lod1_dist.get(k, 0) for k in [('c_spine1', 'c_spine2'), ('c_spine2', 'c_spine3'), ('c_spine3', 'c_neck')]])
        hf_total = sum([hf_dist.get(k, 0) for k in [('SpineMiddle', 'SpineUpper'), ('SpineUpper', 'Chest'), ('Chest', 'Neck')]])
        print(f'\nTotal (SpineMiddle/c_spine1 to Neck):')
        print(f'  LOD1: {lod1_total:.4f} cm')
        print(f'  HF:   {hf_total:.4f} cm')
        print(f'  Diff: {lod1_total - hf_total:+.4f} cm')

        # World positions comparison
        print('\n=== WORLD Y POSITION COMPARISON ===')
        print(f'{"LOD1 Joint":15} {"Y (cm)":10} {"HF Joint":15} {"Y (cm)":10} {"Diff":10}')
        print('-' * 60)

        joint_mappings = [
            ('c_spine1', 'SpineMiddle'),
            ('c_spine2', 'SpineUpper'),
            ('c_spine3', 'Chest'),
            ('c_neck', 'Neck'),
        ]

        for lod1_j, hf_j in joint_mappings:
            lod1_y = lod1_pos.get(lod1_j, np.array([0,0,0]))[1]
            hf_y = hf_pos.get(hf_j, np.array([0,0,0]))[1]
            diff = lod1_y - hf_y
            print(f'{lod1_j:15} {lod1_y:10.4f} {hf_j:15} {hf_y:10.4f} {diff:+10.4f}')


if __name__ == '__main__':
    main()

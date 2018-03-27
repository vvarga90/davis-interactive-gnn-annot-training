import numpy as np

from .operations import bezier_curve, bresenham


def scribbles2mask(scribbles,
                   output_resolution,
                   only_annotated_frame=False,
                   bezier_curve_sampling=False,
                   nb_points=1000,
                   bresenham_=True,
                   default_value=-1):
    """ Convert the scribbles data into a mask.

    Args:
        scribbles (dict): Scribbles in the default format
        output_resolution (tuple): Output resolution (H, W).
        only_annotated_frame (bool): Weather return the mask for all the frames
            or only the mask of the single annotated frame (only valid if one
            frame is annotated). Default False.
        bezier_curve_sampling (bool): Weather sample first the returned
            scribbles using bezier curve.
        nb_points (int): If `bezier_curve_sampling` is `True` set the number of
            points to sample from the bezier curve. Default 1000.
        bresenham (bool): Wether to compute bresenham algorithm for the
            scribbles lines.
        default_value (int): default value for the pixels which do not belong
            to any scribble.

    Returns:
        (ndarray): Array with the mask of the scribbles with the index of the
            object ids. The shape of the returned array is (B x H x W) by
            default or (H x W) if `only_annotated_frame==True`.
    """
    if len(output_resolution) != 2:
        raise ValueError(f'Invalid output resolution: {output_resolution}')
    for r in output_resolution:
        if r < 1:
            raise ValueError(f'Invalid output resolution: {output_resolution}')

    nb_frames = len(scribbles['scribbles'])
    masks = np.full(
        (nb_frames, ) + output_resolution, default_value, dtype=np.int)

    size_array = np.asarray(output_resolution[::-1], dtype=np.float) - 1

    for f in range(nb_frames):
        sp = scribbles['scribbles'][f]
        for p in sp:
            path = p['path']
            obj_id = p['object_id']
            path = np.asarray(path, dtype=np.float)
            if bezier_curve_sampling:
                path = bezier_curve(path, nb_points=nb_points)
            path *= size_array
            path = path.astype(np.int)

            if bresenham_:
                path = bresenham(path)
            m = masks[f]

            m[path[:, 1], path[:, 0]] = obj_id
            masks[f] = m

    if only_annotated_frame:
        if 'annotated_frame' not in scribbles:
            raise ValueError('`annotated_frame` not in scribble')
        annotated_frame = scribbles['annotated_frame']
        return masks[annotated_frame]

    return masks


def scribbles2points(scribbles_data, output_resolution=None):
    """ Convert the given scribbles into a list of points and object ids.

    Args:
        scribbles_data (dict): Scribbles in the default format
        output_resolution (tuple): Output resolution (H, W) to scale the
            points.
            If None given, the points will be floats as a fraction of height
            and width.
    Returns:
        (ndarray, ndarray): Returns (X, Y) where X is a list of points from the
            scribbles represented in the output_resolution with shape (N x 2)
            being N the total number of points on all the scribbles. Y is the
            object id for each given point with shape (N,).
    """
    scribbles = scribbles_data['scribbles']

    paths, object_ids = [], []

    for s in scribbles:
        for l in s:
            p = l['path']
            paths += p
            object_ids += [l['object_id']] * len(p)

    paths = np.asarray(paths, dtype=np.float)
    object_ids = np.asarray(object_ids, dtype=np.int)

    if output_resolution:
        img_size = np.asarray(output_resolution, dtype=np.float)
        img_size = img_size[::-1] - 1
        paths *= img_size
        paths = paths.astype(np.int)

    return paths, object_ids


def fuse_scribbles(scribbles_a, scribbles_b):
    """ Fuse two scribbles in the default format.

    Args:
        scribbles_a (dict): Default representation of scribbles A.
        scribbles_b (dict): Default representation of scribbles B.

    Returns:
        (dict): Return a dictionary being the representation of the addition of
            both scribbles A and B.
    """

    assert scribbles_a['sequence'] == scribbles_b[
        'sequence'], 'Scribbles to fuse not from the same sequence'
    assert len(scribbles_a['scribbles']) == len(scribbles_b[
        'scribbles']), 'Scribbles does not have the same number of frames'

    scribbles = dict(scribbles_a)
    nb_frames = len(scribbles['scribbles'])

    for i in range(nb_frames):
        scribbles['scribbles'][i] += scribbles_b['scribbles'][i]

    return scribbles


def is_empty(scribbles_data):
    """ Checks wether the given scribble has any line.

    Args:
        scribbles_data (dict): Scribble in the default format
    """
    scribbles = scribbles_data['scribbles']
    has_lines = [len(s) > 0 for s in scribbles]
    return any(has_lines)

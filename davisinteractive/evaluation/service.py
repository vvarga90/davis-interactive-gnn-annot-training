import numpy as np
import pandas as pd

from ..dataset.davis import Davis
from ..metrics import batched_jaccard
from ..robot import InteractiveScribblesRobot


class EvaluationService:

    VALID_SUBSETS = ['train', 'val', 'test-dev']
    REPORT_COLUMNS = [
        'sequence', 'scribble_idx', 'interaction', 'object_id', 'frame',
        'jaccard', 'timming'
    ]
    ROBOT_DEFAULT_PARAMETERS = {
        'kernel_size': .2,
        'min_nb_nodes': 4,
        'nb_points': 1000
    }

    def __init__(self, davis_root=None, robot_parameters=None):
        self.davis = Davis(davis_root=davis_root)
        self.session_started = False

        robot_parameters = robot_parameters or self.ROBOT_DEFAULT_PARAMETERS
        self.robot = InteractiveScribblesRobot(**robot_parameters)

        self.sequences = None
        self.sequences_scribble_idx = None
        self.report = None

    def start(self, subset):
        if subset not in self.davis.sets:
            raise ValueError(
                f'Subset must be a valid subset: {self.davis.sets.keys()}')

        # Get the list of sequences to evaluate and also from all the scribbles
        # available
        # sequences = DAVIS.sets[subset]
        # self.sequences_counter = {s: 0 for s in sequences}
        self.sequences = self.davis.sets[subset]
        self.sequences_scribble_idx = []
        for s in self.sequences:
            nb_scribbles = self.davis.dataset['sequences'][s]['num_scribbles']
            for i in range(1, nb_scribbles + 1):
                self.sequences_scribble_idx.append((s, i))

        # Check all the files are placed
        self.davis.check_files(self.sequences)

        # Create empty report
        self.report = pd.DataFrame(columns=self.REPORT_COLUMNS)

        self.session_started = True
        max_t, max_i = None, None
        return self.sequences_scribble_idx, max_t, max_i

    def get_starting_scribble(self, sequence, scribble_idx):
        if not self.session_started:
            raise RuntimeError('Session not started')
        if sequence not in self.sequences:
            raise ValueError(f'Invalid sequence: {sequence}')
        if (sequence, scribble_idx) not in self.sequences_scribble_idx:
            raise ValueError(f'Invalid scribble index: {scribble_idx}')

        scribble = self.davis.load_scribble(sequence, scribble_idx)

        return scribble

    def submit_masks(self, sequence, scribble_idx, pred_masks, timming,
                     interaction):
        # Evaluate the submitted masks
        if len(self.report.loc[(self.report.sequence == sequence)
                               & (self.report.scribble_idx == scribble_idx) &
                               (self.report.interaction == interaction)]) > 0:
            raise RuntimeError(
                f'For {sequence} and scribble {scribble_idx} already exist a result for interaction {interaction}'
            )
        if interaction > 1 and len(
                self.report.loc[(self.report.sequence == sequence)
                                & (self.report.scribble_idx == scribble_idx) &
                                (self.report.interaction == interaction -
                                 1)]) == 0:
            raise RuntimeError(
                f'For {sequence} and scribble {scribble_idx} does not exist a result for previous interaction {interaction-1}'
            )
        gt_masks = self.davis.load_annotations(sequence)
        jaccard = batched_jaccard(
            gt_masks, pred_masks, average_over_objects=False)
        nb_frames, nb_objects = jaccard.shape
        nb = nb_frames * nb_objects

        frames_idx = np.arange(nb_frames)
        objects_idx = np.arange(nb_objects)

        objects_idx, frames_idx = np.meshgrid(objects_idx, frames_idx)

        uploaded_result = {k: None for k in self.REPORT_COLUMNS}
        uploaded_result['sequence'] = [sequence] * nb
        uploaded_result['scribble_idx'] = [scribble_idx] * nb
        uploaded_result['interaction'] = [interaction] * nb
        uploaded_result['timming'] = [timming] * nb
        uploaded_result['object_id'] = objects_idx.ravel().tolist()
        uploaded_result['frame'] = frames_idx.ravel().tolist()
        uploaded_result['jaccard'] = jaccard.ravel().tolist()
        uploaded_result = pd.DataFrame(
            data=uploaded_result, columns=self.REPORT_COLUMNS)
        self.report = pd.concat(
            [self.report, uploaded_result], ignore_index=True)

        # Generate next scribble
        next_scribble = self.robot.interact(sequence, pred_masks, gt_masks)

        return next_scribble

    def get_report(self):
        return self.report

    def close(self):
        pass

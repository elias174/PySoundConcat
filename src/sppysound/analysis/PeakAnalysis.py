from __future__ import print_function, division
import os
import numpy as np
import logging
from scipy import signal
from numpy.lib import stride_tricks
import pdb


from fileops import pathops

from Analysis import Analysis

logger = logging.getLogger(__name__)


class PeakAnalysis(Analysis):

    """
    An encapsulation of the Peak analysis of an AnalysedAudioFile.

    On initialization, the Peak analysis is either created, or a pre existing
    file already exists.
    In either case, once the file is generated, it's values can be obtained
    through use of the get_peak_from_file method

    Note: Due to the large size of Peak analysis it is not stored in a class
    member as other such analyses are. Use get_peak_from_file.
    """

    def __init__(self, AnalysedAudioFile, analysis_group, config=None):
        super(PeakAnalysis, self).__init__(AnalysedAudioFile, analysis_group, 'Peak')
        self.logger = logging.getLogger(__name__+'.{0}Analysis'.format(self.name))
        # Store reference to the file to be analysed
        self.AnalysedAudioFile = AnalysedAudioFile

        self.analysis_group = analysis_group
        frames = self.AnalysedAudioFile.read_grain()
        self.logger.info("Creating Peak analysis for {0}".format(self.AnalysedAudioFile.name))
        self.create_analysis(frames)

    @staticmethod
    def create_peak_analysis(frames, window_size=512,
                            window=signal.triang,
                            overlapFac=0.5):
        """
        Generate an energy contour analysis.

        Calculate the Peak values of windowed segments of the audio file and
        save to disk.
        """
        # Calculate the period of the window in hz
        # lowest_freq = 1.0 / window_size
        # Filter frequencies lower than the period of the window
        # filter = ButterFilter()
        # filter.design_butter(lowest_freq, self.AnalysedAudioFile.samplerate)
        # TODO: Fix filter
        # frames = filter.filter_butter(frames)

        # Generate a window function to apply to peak windows before analysis
        win = window(window_size)
        hopSize = int(window_size - np.floor(overlapFac * window_size))

        # zeros at beginning (thus center of 1st window should be for sample nr. 0)
        samples = np.append(np.zeros(np.floor(window_size/2.0)), frames)

        # cols for windowing
        cols = np.ceil((len(samples) - window_size) / float(hopSize)) + 1
        # zeros at end (thus samples can be fully covered by frames)
        samples = np.append(samples, np.zeros(window_size))

        frames = stride_tricks.as_strided(
            samples,
            shape=(cols, window_size),
            strides=(samples.strides[0]*hopSize, samples.strides[0])
        ).copy()

        frames *= win
        peak = np.max(np.abs(frames), axis=1)

        return peak

    def get_analysis_grains(self, start, end):
        """
        Retrieve analysis frames for period specified in start and end times.
        arrays of start and end time pairs will produce an array of equivelant
        size containing frames for these times.
        """
        times = self.analysis_group["Peak"]["times"][:]
        start = start / 1000
        end = end / 1000
        vtimes = times.reshape(-1, 1)

        selection = np.transpose((vtimes >= start) & (vtimes <= end))

        grain_data = [[],[]]
        for grain in selection:
            grain_data[0].append(self.analysis_group["Peak"]["frames"][grain])
            grain_data[1].append(times[grain])

        return grain_data

    def hdf5_dataset_formatter(self, *args, **kwargs):
        '''
        Formats the output from the analysis method to save to the HDF5 file.
        '''
        samplerate = self.AnalysedAudioFile.samplerate
        peak = self.create_peak_analysis(*args, **kwargs)
        peak_times = self.calc_peak_frame_times(peak, args[0], samplerate)
        return ({'frames': peak, 'times': peak_times}, {})

    @staticmethod
    def calc_peak_frame_times(peakframes, sample_frames, samplerate):

        """Calculate times for frames using sample size and samplerate."""

        # Get number of frames for time and frequency
        timebins = peakframes.shape[0]
        # Create array ranging from 0 to number of time frames
        scale = np.arange(timebins+1)
        # divide the number of samples by the total number of frames, then
        # multiply by the frame numbers.
        peak_times = (float(sample_frames.shape[0])/float(timebins)) * scale[:-1].astype(float)
        # Divide by the samplerate to give times in seconds
        peak_times = peak_times / samplerate
        return peak_times

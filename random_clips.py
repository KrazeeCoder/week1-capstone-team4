#call load_audio() to get samples and sample rate
#then call make_random_clips 
import numpy as np


def make_random_clip(samples: np.ndarray, clip_length: float, sample_rate: int, rng: np.random.Generator):
    
   #Gives a random clip (based on a given length) from an array (the longer one) of audio samples.
 #Before: call load_audio() to get samples and sample rate then call make_random_clips

    num_clips = int(clip_length * sample_rate)

    if num_clips > len(samples):
        raise ValueError("The clip length you asked for is longer than the recording")

    max_start = len(samples) - num_clips #las valid starting point
    start_idx = rng.integers(0, max_start + 1)

    return samples[start_idx : start_idx + num_clips]


def make_random_clips(samples: np.ndarray, clip_length: float, num_clips: int, sample_rate: int):

    #Calls make_random_clip repeatedly.
    #Parameters:
    #samples 
    #clip_length : float, length of clip → in secs
    #sampling_rate : 44100 (in Hz)
    #Returns:
    #np.ndarray, shape-(clip_num_samples,)
    #A random clip of `samples`


    rng = np.random.default_rng()

    return [
        make_random_clip(samples, clip_length, sample_rate, rng) for i in range(num_clips)
    ]

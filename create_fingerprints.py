from typing import List, Tuple


def peaks_to_fingerprints(
    peaks: List[Tuple[int, int]], fanout: int = 15
) -> List[Tuple[Tuple[int, int, int], int]]:
    fingerprints = []
    #loop over every peak, treating each as the anchor
    for i, (anchor_freq, anchor_time) in enumerate(peaks):

        #pair this anchor with the next fanout peaks
        for j in range(1, fanout + 1):
            if i + j < len(peaks):
                other_freq, other_time = peaks[i + j]
                #compute the time gap between the two peaks.
                delta_t = other_time - anchor_time

                quantized_fingerprint = (
                    anchor_freq // 4,
                    other_freq // 4,
                    delta_t // 2,
                )
            fingerprints.append((quantized_fingerprint, anchor_time))

    return fingerprints
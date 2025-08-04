import numpy as np


element_positions = [-0.00182, -0.00171, -0.0016, -0.00149, -0.00138, -0.00127, -0.00116, -0.00105,
                     -0.000935, -0.000825, -0.000715, -0.000605, -0.000495, -0.000385, -0.000275, -0.00022,
                     0.00022,  0.000275,  0.000385,  0.000495,  0.000605,  0.000715,  0.000825,  0.000935,
                     0.00105,  0.00116,  0.00127,  0.00138,  0.00149,  0.0016,  0.00171,  0.00182]

def compute_focus_delays(
    num_elements=16,
    pitch_um=110,
    focus_point_mm=(0.0, 15.0),
    c=1076.5,
    delay_resolution_ns=4
):
    pitch = pitch_um * 1e-6
    x_focus, z_focus = focus_point_mm[0] / 1000, focus_point_mm[1] / 1000

    element_indices = np.arange(-(num_elements-1)/2, (num_elements+1)/2)
    x_positions = element_indices * pitch

    distances = np.sqrt((x_positions - x_focus)**2 + z_focus**2)
    reference = np.min(distances)
    delays = (distances - reference) / c  # in seconds

    delay_resolution = delay_resolution_ns * 1e-9
    delay_ticks = np.round(delays / delay_resolution).astype(int)
    return delay_ticks

if __name__ == "__main__":
    delays = compute_focus_delays()
    print(delays)

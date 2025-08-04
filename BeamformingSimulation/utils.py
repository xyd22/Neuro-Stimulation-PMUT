import numpy as np
import matplotlib.pyplot as plt
import cvxpy as cp

# Function to calculate the speed of sound in water based on temperature
def speed_of_sound_in_water(T):
    return 1449.2 + 4.6 * T - 0.055 * T**2 + 0.00029 * T**3

# Calculate steering vector
def steering_vector(theta, array_positions, wavelength):
    k = 2 * np.pi / wavelength
    angles_rad = np.deg2rad(theta)
    array_positions = np.array(array_positions)  # Convert to numpy array
    steering = np.exp(-1j * k * array_positions * np.sin(angles_rad))
    return steering

# Convex Optimization-based Beamforming function with paired phase constraints
def convex_optimization_beamforming(theta_s, element_positions, wavelength, interference_directions, noise_power=0.1, interference_power=[1]):
    num_pairs = len(element_positions) // 2  # Number of pairs
    v_s = steering_vector(theta_s, element_positions, wavelength)
    v_i = [steering_vector(theta, element_positions, wavelength) for theta in interference_directions]

    # Define the optimization variables and constraints
    w_pair = cp.Variable(num_pairs, complex=True)  # Shared weights for each pair
    w = cp.hstack([w_pair[i//2] for i in range(len(element_positions))])  # Repeat weights for each pair of nodes

    constraints = [cp.norm(w) <= 1]  # Constraint to ensure weights are normalized
    interference_constraints = [cp.abs(w.H @ v_i[k]) <= np.sqrt(interference_power[k]) for k in range(len(v_i))]

    # Define the problem
    objective = cp.Minimize(cp.quad_form(w, np.eye(len(element_positions)) * noise_power) - cp.real(w.H @ v_s))
    prob = cp.Problem(objective, constraints + interference_constraints)

    # Solve the problem
    prob.solve()
    w_opt = w.value
    return w_opt

# Post-process the weights to match the chip's specifications
def post_process_weights(weights, discretized_phase_shift, discrete_amplitudes):
    # Normalize weights
    max_magnitude = np.max(np.abs(weights))
    normalized_weights = weights / max_magnitude

    phases = np.angle(normalized_weights)
    magnitudes = np.abs(normalized_weights)

    # Quantize phases
    quantized_phases = np.round(phases / (discretized_phase_shift / 2)) * (discretized_phase_shift / 2)

    # Discretize amplitudes
    quantized_magnitudes = np.zeros_like(magnitudes)
    for i in range(len(magnitudes)):
        quantized_magnitudes[i] = min(discrete_amplitudes, key=lambda x: abs(x - magnitudes[i]))

    quantized_weights = quantized_magnitudes * np.exp(1j * quantized_phases)
    return quantized_weights, quantized_magnitudes, quantized_phases

# Function to print power, phase shift, amplitude, clock cycles, encoded delay, hex value, and clock cycles in seconds
def print_weights_info(weights, magnitudes, phases, discretized_phase_shift):
    clock_cycles = np.round(phases / (discretized_phase_shift / 2)).astype(int)
    min_clock_cycle = np.min(clock_cycles)
    adjusted_clock_cycles = (clock_cycles - min_clock_cycle) / 2  # Adjust clock cycles and divide by 2

    def encode_clock_cycles_to_hex(clock_cycle):
        # Convert to integer and separate integer and fractional parts
        integer_part = int(np.floor(clock_cycle))
        fractional_part = int((clock_cycle - integer_part) * 2)

        # Encode the value
        encoded_value = (integer_part & 0x3FFF) | (fractional_part << 14)
        return f"{encoded_value:04X}"

    hex_values = []
    for clock_cycle in adjusted_clock_cycles:
        hex_value = encode_clock_cycles_to_hex(clock_cycle)
        hex_values.append(hex_value)

    return hex_values

# Combine hex values into 8-digit hex numbers
def combine_hex_values(hex_values):
    combined_hex_values = []
    for i in range(0, len(hex_values), 2):
        combined_hex = hex_values[i + 1] + hex_values[i]
        combined_hex_values.append("0x" + combined_hex)
    return combined_hex_values
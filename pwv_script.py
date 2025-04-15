"""
PTT and PWV Calculator for Existing CSV Data
Processes PPG data to calculate PTT and PWV based on systolic and diastolic peaks.
"""

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import os
from datetime import datetime

def process_csv_file(csv_file_path, distance_cm=20):
    # Create output folder
    output_folder = "ptt_pwv_results"
    os.makedirs(output_folder, exist_ok=True)
    
    # Load the CSV data
    try:
        data = pd.read_csv(csv_file_path)
        print(f"Successfully loaded data with {len(data)} rows")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return None
    
    # Extract data columns
    timestamps = data['timestamp_ms'].values
    ppg1 = data['ppg1'].values
    ppg2 = data['ppg2'].values
    
    # Apply filtering
    window_size = 5
    ppg1_filtered = np.convolve(ppg1, np.ones(window_size)/window_size, mode='valid')
    ppg2_filtered = np.convolve(ppg2, np.ones(window_size)/window_size, mode='valid')
    timestamps_filtered = timestamps[window_size-1:]
    
    # Calculate derivatives
    ppg1_vpg = np.gradient(ppg1_filtered)
    ppg2_vpg = np.gradient(ppg2_filtered)
    
    # Find systolic peaks
    ppg1_systolic_peaks, _ = find_peaks(ppg1_filtered, height=np.mean(ppg1_filtered), distance=30)
    ppg2_systolic_peaks, _ = find_peaks(ppg2_filtered, height=np.mean(ppg2_filtered), distance=30)
    
    print(f"Found {len(ppg1_systolic_peaks)} systolic peaks in PPG1 and {len(ppg2_systolic_peaks)} systolic peaks in PPG2")
    
    # Find diastolic peaks
    ppg1_diastolic_peaks = []
    ppg2_diastolic_peaks = []
    
    # For PPG1: Find diastolic peaks after each systolic peak
    for peak in ppg1_systolic_peaks:
        search_start = peak + 10
        search_end = min(peak + 100, len(ppg1_filtered) - 1)
        
        if search_start >= search_end:
            continue
        
        diastolic_candidates, _ = find_peaks(ppg1_filtered[search_start:search_end], 
                                           height=0.3*ppg1_filtered[peak])
        
        if len(diastolic_candidates) > 0:
            diastolic_peak = search_start + diastolic_candidates[0]
            ppg1_diastolic_peaks.append(diastolic_peak)
    
    # For PPG2: Find diastolic peaks after each systolic peak
    for peak in ppg2_systolic_peaks:
        search_start = peak + 10
        search_end = min(peak + 100, len(ppg2_filtered) - 1)
        
        if search_start >= search_end:
            continue
        
        diastolic_candidates, _ = find_peaks(ppg2_filtered[search_start:search_end], 
                                           height=0.3*ppg2_filtered[peak])
        
        if len(diastolic_candidates) > 0:
            diastolic_peak = search_start + diastolic_candidates[0]
            ppg2_diastolic_peaks.append(diastolic_peak)
    
    print(f"Found {len(ppg1_diastolic_peaks)} diastolic peaks in PPG1 and {len(ppg2_diastolic_peaks)} diastolic peaks in PPG2")
    
    # Calculate PTT using systolic peaks (peak-to-peak)
    ptt_systolic = calculate_ptt(timestamps_filtered, ppg1_systolic_peaks, ppg2_systolic_peaks)
    
    # Calculate PTT using diastolic peaks
    ptt_diastolic = calculate_ptt(timestamps_filtered, ppg1_diastolic_peaks, ppg2_diastolic_peaks)
    
    # Calculate PWV if distance is provided
    pwv_systolic = []
    pwv_diastolic = []
    
    if distance_cm > 0:
        # Convert distance from cm to meters
        distance_m = distance_cm / 100.0
        
        # Calculate PWV for each PTT value (convert PTT from ms to seconds)
        if ptt_systolic:
            pwv_systolic = [distance_m / (ptt / 1000.0) for ptt in ptt_systolic]
            print(f"Systolic Peak: Avg PWV = {np.mean(pwv_systolic):.2f} m/s")
        
        if ptt_diastolic:
            pwv_diastolic = [distance_m / (ptt / 1000.0) for ptt in ptt_diastolic]
            print(f"Diastolic Peak: Avg PWV = {np.mean(pwv_diastolic):.2f} m/s")
    
    # Print PTT statistics
    if ptt_systolic:
        print(f"Systolic Peak: Avg PTT = {np.mean(ptt_systolic):.2f} ms, STD = {np.std(ptt_systolic):.2f} ms")
    if ptt_diastolic:
        print(f"Diastolic Peak: Avg PTT = {np.mean(ptt_diastolic):.2f} ms, STD = {np.std(ptt_diastolic):.2f} ms")
    
    # Create timestamp for filenames
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = os.path.basename(csv_file_path).replace("_raw_data.csv", "")
    result_filename_base = f"{base_filename}_analysis_{timestamp_str}"
    
    # Create and save plots
    create_plots(
        timestamps_filtered, ppg1_filtered, ppg2_filtered,
        ppg1_systolic_peaks, ppg2_systolic_peaks, 
        ppg1_diastolic_peaks, ppg2_diastolic_peaks,
        ptt_systolic, ptt_diastolic, 
        pwv_systolic, pwv_diastolic,
        distance_cm, output_folder, result_filename_base
    )
    
    # Save results to CSV
    save_results(
        ptt_systolic, ptt_diastolic, 
        pwv_systolic, pwv_diastolic,
        distance_cm, output_folder, result_filename_base
    )
    
    return {
        "ptt_systolic": ptt_systolic,
        "ptt_diastolic": ptt_diastolic,
        "pwv_systolic": pwv_systolic,
        "pwv_diastolic": pwv_diastolic
    }

def calculate_ptt(timestamps, indices1, indices2):
    """Calculate PTT between two sets of indices"""
    ptt_values = []
    
    # Use the minimum number of indices from both signals
    min_indices = min(len(indices1), len(indices2))
    
    for i in range(min_indices):
        # Calculate time difference between corresponding features
        ptt = timestamps[indices2[i]] - timestamps[indices1[i]]
        
        # Only add valid PTT values (positive and reasonable)
        if 0 < ptt < 300:  # PTT typically less than 300ms
            ptt_values.append(ptt)
    
    return ptt_values

def create_plots(timestamps, ppg1, ppg2,
                ppg1_systolic_peaks, ppg2_systolic_peaks,
                ppg1_diastolic_peaks, ppg2_diastolic_peaks,
                ptt_systolic, ptt_diastolic,
                pwv_systolic, pwv_diastolic,
                distance_cm, output_folder, filename_base):
    """Create and save plots in separate files as requested"""
    
    # 1. PPG Waveforms Plot
    fig_ppg, axes_ppg = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot PPG1 signal with systolic and diastolic peaks
    axes_ppg[0].plot(timestamps, ppg1, 'r-', label='PPG Sensor 1')
    if len(ppg1_systolic_peaks) > 0:
        axes_ppg[0].plot(timestamps[ppg1_systolic_peaks], ppg1[ppg1_systolic_peaks], 'ro', label='Peaks')
    if len(ppg1_diastolic_peaks) > 0:
        axes_ppg[0].plot(timestamps[ppg1_diastolic_peaks], ppg1[ppg1_diastolic_peaks], 'rx', label='Feet')
    axes_ppg[0].set_title('PPG Signal 1')
    axes_ppg[0].set_ylabel('Amplitude')
    axes_ppg[0].legend()
    
    # Plot PPG2 signal with systolic and diastolic peaks
    axes_ppg[1].plot(timestamps, ppg2, 'b-', label='PPG Sensor 2')
    if len(ppg2_systolic_peaks) > 0:
        axes_ppg[1].plot(timestamps[ppg2_systolic_peaks], ppg2[ppg2_systolic_peaks], 'bo', label='Peaks')
    if len(ppg2_diastolic_peaks) > 0:
        axes_ppg[1].plot(timestamps[ppg2_diastolic_peaks], ppg2[ppg2_diastolic_peaks], 'bx', label='Feet')
    axes_ppg[1].set_title('PPG Signal 2')
    axes_ppg[1].set_xlabel('Time (ms)')
    axes_ppg[1].set_ylabel('Amplitude')
    axes_ppg[1].legend()
    
    plt.tight_layout()
    ppg_filename = os.path.join(output_folder, f"{filename_base}_ppg_signals.png")
    plt.savefig(ppg_filename, dpi=300)
    plt.close(fig_ppg)
    print(f"PPG plots saved to: {ppg_filename}")
    
    # 2. PTT Waveform Plot
    if ptt_systolic or ptt_diastolic:
        fig_ptt, axes_ptt = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot systolic PTT values
        if ptt_systolic:
            axes_ptt[0].plot(range(len(ptt_systolic)), ptt_systolic, 'g-o', label='Systolic Peak PTT')
            axes_ptt[0].axhline(y=np.mean(ptt_systolic), color='g', linestyle='--')
            axes_ptt[0].set_title('Pulse Transit Time (Systolic Peaks)')
            axes_ptt[0].set_ylabel('PTT (ms)')
            axes_ptt[0].legend()
        
        # Plot diastolic PTT values
        if ptt_diastolic:
            axes_ptt[1].plot(range(len(ptt_diastolic)), ptt_diastolic, 'm-o', label='Diastolic Peak PTT')
            axes_ptt[1].axhline(y=np.mean(ptt_diastolic), color='m', linestyle='--')
            axes_ptt[1].set_title('Pulse Transit Time (Diastolic Peaks)')
            axes_ptt[1].set_xlabel('Measurement Number')
            axes_ptt[1].set_ylabel('PTT (ms)')
            axes_ptt[1].legend()
        
        # Add text below the plot with average values
        ptt_text = ""
        if ptt_systolic:
            ptt_text += f"Average Systolic PTT: {np.mean(ptt_systolic):.2f} ms (SD: {np.std(ptt_systolic):.2f} ms)\n"
        if ptt_diastolic:
            ptt_text += f"Average Diastolic PTT: {np.mean(ptt_diastolic):.2f} ms (SD: {np.std(ptt_diastolic):.2f} ms)"
        
        plt.figtext(0.5, 0.01, ptt_text, ha='center', fontsize=12)
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        
        ptt_filename = os.path.join(output_folder, f"{filename_base}_ptt_values.png")
        plt.savefig(ptt_filename, dpi=300)
        plt.close(fig_ptt)
        print(f"PTT plots saved to: {ptt_filename}")
    
    # 3. PWV Plot
    if pwv_systolic or pwv_diastolic:
        fig_pwv, axes_pwv = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot systolic PWV values
        if pwv_systolic:
            axes_pwv[0].plot(range(len(pwv_systolic)), pwv_systolic, 'g-o', label='Systolic PWV')
            axes_pwv[0].axhline(y=np.mean(pwv_systolic), color='g', linestyle='--')
            axes_pwv[0].set_title('Pulse Wave Velocity (Systolic Peaks)')
            axes_pwv[0].set_ylabel('PWV (m/s)')
            axes_pwv[0].legend()
        
        # Plot diastolic PWV values
        if pwv_diastolic:
            axes_pwv[1].plot(range(len(pwv_diastolic)), pwv_diastolic, 'm-o', label='Diastolic PWV')
            axes_pwv[1].axhline(y=np.mean(pwv_diastolic), color='m', linestyle='--')
            axes_pwv[1].set_title('Pulse Wave Velocity (Diastolic Peaks)')
            axes_pwv[1].set_xlabel('Measurement Number')
            axes_pwv[1].set_ylabel('PWV (m/s)')
            axes_pwv[1].legend()
        
        # Add text below the plot with average values
        pwv_text = f"Distance between sensors: {distance_cm} cm\n"
        if pwv_systolic:
            pwv_text += f"Average Systolic PWV: {np.mean(pwv_systolic):.2f} m/s (SD: {np.std(pwv_systolic):.2f} m/s)\n"
        if pwv_diastolic:
            pwv_text += f"Average Diastolic PWV: {np.mean(pwv_diastolic):.2f} m/s (SD: {np.std(pwv_diastolic):.2f} m/s)"
        
        plt.figtext(0.5, 0.01, pwv_text, ha='center', fontsize=12)
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        
        pwv_filename = os.path.join(output_folder, f"{filename_base}_pwv_values.png")
        plt.savefig(pwv_filename, dpi=300)
        plt.close(fig_pwv)
        print(f"PWV plots saved to: {pwv_filename}")

def save_results(ptt_systolic, ptt_diastolic, pwv_systolic, pwv_diastolic, distance_cm, output_folder, filename_base):
    """Save the results to a CSV file"""
    # Create a DataFrame for the results
    results = pd.DataFrame()
    
    # Add systolic PTT values
    if ptt_systolic:
        results['ptt_systolic_ms'] = pd.Series(ptt_systolic)
    
    # Add diastolic PTT values
    if ptt_diastolic:
        results['ptt_diastolic_ms'] = pd.Series(ptt_diastolic)
    
    # Add PWV values if available
    if pwv_systolic:
        results['pwv_systolic_m_s'] = pd.Series(pwv_systolic)
    
    if pwv_diastolic:
        results['pwv_diastolic_m_s'] = pd.Series(pwv_diastolic)
    
    # Add metadata
    results['distance_cm'] = distance_cm
    results['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add summary statistics as additional rows
    summary = pd.DataFrame({
        'ptt_systolic_ms': [np.nan, np.mean(ptt_systolic) if ptt_systolic else np.nan, np.std(ptt_systolic) if ptt_systolic else np.nan],
        'ptt_diastolic_ms': [np.nan, np.mean(ptt_diastolic) if ptt_diastolic else np.nan, np.std(ptt_diastolic) if ptt_diastolic else np.nan],
        'pwv_systolic_m_s': [np.nan, np.mean(pwv_systolic) if pwv_systolic else np.nan, np.std(pwv_systolic) if pwv_systolic else np.nan],
        'pwv_diastolic_m_s': [np.nan, np.mean(pwv_diastolic) if pwv_diastolic else np.nan, np.std(pwv_diastolic) if pwv_diastolic else np.nan],
        'distance_cm': [np.nan, distance_cm, np.nan],
        'timestamp': [np.nan, 'MEAN', 'STD']
    })
    
    results = pd.concat([results, summary], ignore_index=True)
    
    # Save to CSV
    results_filename = os.path.join(output_folder, f"{filename_base}_results.csv")
    results.to_csv(results_filename, index=False)
    print(f"Results saved to: {results_filename}")

def main():
    """Main function to process a CSV file"""
    # Default distance between sensors in centimeters
    distance_cm = 20
    
    # Ask for the CSV file path
    csv_file = input("Enter the path to the raw CSV file: ")
    
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        return
    
    # Ask for the distance between sensors
    distance_input = input(f"Enter the distance between sensors in centimeters (default: {distance_cm}): ")
    if distance_input.strip():
        try:
            distance_cm = float(distance_input)
        except ValueError:
            print(f"Invalid distance value. Using default: {distance_cm} cm")
    
    # Process the CSV file
    process_csv_file(csv_file, distance_cm)

if __name__ == "__main__":
    main()

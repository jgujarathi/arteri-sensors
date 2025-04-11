"""
PTT (Pulse Transit Time) Calculator
This script connects to an Arduino MKRZero via USB, receives PPG data from two sensors,
detects peaks using scipy, calculates PTT, and saves plots to a folder.
"""

import serial
import time
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import serial.tools.list_ports
import os
from datetime import datetime

class PTTCalculator:
    def __init__(self, output_folder="ptt_plots"):
        self.ser = None
        self.ppg1_data = []
        self.ppg2_data = []
        self.timestamps = []
        self.ptt_values = []
        self.all_ptt_values = []  # For storing all PTT values across sessions
        self.is_collecting = False
        self.collection_count = 0
        
        # Create output folder if it doesn't exist
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)
        print(f"Plots will be saved to: {os.path.abspath(self.output_folder)}")

    def connect_to_arduino(self):
        """Connect to the Arduino MKRZero via USB"""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            print(f"Found port: {p}")
        
        port = input("Enter the Arduino port name (e.g. COM3 or /dev/ttyACM0): ")
        try:
            self.ser = serial.Serial(port, 115200)
            print(f"Connected to Arduino on {port}")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to Arduino: {e}")
            return False

    def process_data(self):
        """Process the collected data to find peaks and calculate PTT"""
        if len(self.ppg1_data) < 50 or len(self.ppg2_data) < 50:
            print("Not enough data points collected")
            return
        
        self.collection_count += 1
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"collection_{timestamp_str}"
        
        # Convert data to numpy arrays
        timestamps = np.array(self.timestamps)
        ppg1 = np.array(self.ppg1_data)
        ppg2 = np.array(self.ppg2_data)
        
        # Apply basic filtering (moving average) to smooth the signals
        window_size = 5
        ppg1_filtered = np.convolve(ppg1, np.ones(window_size)/window_size, mode='valid')
        ppg2_filtered = np.convolve(ppg2, np.ones(window_size)/window_size, mode='valid')
        timestamps_filtered = timestamps[window_size-1:]
        
        # Find peaks in both signals
        # Adjust these parameters based on your specific signal characteristics
        ppg1_peaks, _ = find_peaks(ppg1_filtered, height=np.mean(ppg1_filtered), distance=30)
        ppg2_peaks, _ = find_peaks(ppg2_filtered, height=np.mean(ppg2_filtered), distance=30)
        
        print(f"Found {len(ppg1_peaks)} peaks in PPG1 and {len(ppg2_peaks)} peaks in PPG2")
        
        # Calculate PTT for each beat (if enough peaks were detected)
        ptt_values = []
        
        if len(ppg1_peaks) > 0 and len(ppg2_peaks) > 0:
            # Use the minimum number of peaks from both signals
            min_peaks = min(len(ppg1_peaks), len(ppg2_peaks))
            
            for i in range(min_peaks):
                # Calculate time difference between corresponding peaks
                # Assuming first sensor is closer to the heart
                ptt = abs(timestamps_filtered[ppg2_peaks[i]] - timestamps_filtered[ppg1_peaks[i]])
                
                # Only add valid PTT values (positive and reasonable)
                if 0 < ptt < 300:  # PTT typically less than 300ms
                    ptt_values.append(ptt)
            
            if ptt_values:
                avg_ptt = np.mean(ptt_values)
                std_ptt = np.std(ptt_values)
                print(f"Average PTT: {avg_ptt:.2f} ms, STD: {std_ptt:.2f} ms")
                self.ptt_values = ptt_values
                self.all_ptt_values.extend(ptt_values)
            else:
                print("No valid PTT values calculated")
        
        # Create and save plots
        self.save_plots(timestamps_filtered, ppg1_filtered, ppg2_filtered, 
                        ppg1_peaks, ppg2_peaks, ptt_values, filename_base)
        
        # Save the data to a CSV file
        self.save_data(timestamps, ppg1, ppg2, ptt_values, filename_base)
        
        return ptt_values

    def save_plots(self, timestamps, ppg1, ppg2, ppg1_peaks, ppg2_peaks, ptt_values, filename_base):
        """Create and save plots to the output folder"""
        # Create a figure with three subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
        fig.suptitle(f'PTT Analysis - Collection #{self.collection_count}', fontsize=16)
        
        # Plot PPG1 signal and peaks
        ax1.plot(timestamps, ppg1, 'r-', label='PPG Sensor 1')
        if len(ppg1_peaks) > 0:
            ax1.plot(timestamps[ppg1_peaks], ppg1[ppg1_peaks], 'ro', label='Peaks')
        ax1.set_title('PPG Signal 1')
        ax1.set_xlabel('Time (ms)')
        ax1.set_ylabel('Amplitude')
        ax1.legend()
        
        # Plot PPG2 signal and peaks
        ax2.plot(timestamps, ppg2, 'b-', label='PPG Sensor 2')
        if len(ppg2_peaks) > 0:
            ax2.plot(timestamps[ppg2_peaks], ppg2[ppg2_peaks], 'bo', label='Peaks')
        ax2.set_title('PPG Signal 2')
        ax2.set_xlabel('Time (ms)')
        ax2.set_ylabel('Amplitude')
        ax2.legend()
        
        # Plot PTT values
        if ptt_values:
            ax3.plot(range(len(ptt_values)), ptt_values, 'g-o', label='Current PTT Values')
            ax3.axhline(y=np.mean(ptt_values), color='r', linestyle='--', 
                        label=f'Mean: {np.mean(ptt_values):.2f} ms')
        if self.all_ptt_values:
            # Add a small plot showing all PTT values collected so far
            ax_inset = ax3.inset_axes([0.65, 0.1, 0.3, 0.3])
            ax_inset.plot(self.all_ptt_values, 'k-', alpha=0.5)
            ax_inset.set_title('All PTT Values')
            ax_inset.set_xlabel('Sample #')
            ax_inset.set_ylabel('PTT (ms)')
        
        ax3.set_title('Pulse Transit Time')
        ax3.set_xlabel('Measurement Number')
        ax3.set_ylabel('PTT (ms)')
        ax3.legend()
        
        # Add text with statistics
        if ptt_values:
            stats_text = (
                f"Statistics for Collection #{self.collection_count}:\n"
                f"Number of valid PTT values: {len(ptt_values)}\n"
                f"Average PTT: {np.mean(ptt_values):.2f} ms\n"
                f"Standard Deviation: {np.std(ptt_values):.2f} ms\n"
                f"Min PTT: {min(ptt_values):.2f} ms\n"
                f"Max PTT: {max(ptt_values):.2f} ms"
            )
            fig.text(0.1, 0.01, stats_text, fontsize=10)
        
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        
        # Save the figure
        filename = os.path.join(self.output_folder, f"{filename_base}.png")
        plt.savefig(filename, dpi=300)
        plt.close(fig)
        print(f"Plot saved to: {filename}")

    def save_data(self, timestamps, ppg1, ppg2, ptt_values, filename_base):
        """Save the raw data and results to CSV files"""
        # Save raw PPG data
        raw_data = pd.DataFrame({
            'timestamp_ms': timestamps,
            'ppg1': ppg1,
            'ppg2': ppg2
        })
        raw_filename = os.path.join(self.output_folder, f"{filename_base}_raw_data.csv")
        raw_data.to_csv(raw_filename, index=False)
        
        # Save PTT results if available
        if ptt_values:
            ptt_data = pd.DataFrame({
                'ptt_ms': ptt_values
            })
            ptt_data['collection_id'] = self.collection_count
            ptt_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            ptt_filename = os.path.join(self.output_folder, f"{filename_base}_ptt_results.csv")
            ptt_data.to_csv(ptt_filename, index=False)
            
            # Also update a master PTT file with all results
            master_filename = os.path.join(self.output_folder, "all_ptt_results.csv")
            
            if os.path.exists(master_filename):
                master_data = pd.read_csv(master_filename)
                master_data = pd.concat([master_data, ptt_data], ignore_index=True)
            else:
                master_data = ptt_data
                
            master_data.to_csv(master_filename, index=False)
            
        print(f"Data saved to CSV files in: {self.output_folder}")
    
    def collect_data(self):
        """Collect and process data from the Arduino"""
        if not self.ser:
            print("Arduino not connected")
            return
        
        try:
            print("Starting data collection. Press Ctrl+C to stop...")
            while True:
                # Read a line from the serial port
                line = self.ser.readline().decode('utf-8').strip()
                
                # Check for start/end markers
                if line == "START_DATA_COLLECTION":
                    print(f"Starting data collection #{self.collection_count + 1}...")
                    self.is_collecting = True
                    self.ppg1_data = []
                    self.ppg2_data = []
                    self.timestamps = []
                    continue
                
                if line == "END_DATA_COLLECTION":
                    print("Data collection complete. Processing data...")
                    self.is_collecting = False
                    self.process_data()
                    continue
                
                # Parse data if we're in collection mode
                if self.is_collecting:
                    try:
                        parts = line.split(',')
                        if len(parts) == 3:
                            timestamp, ppg1, ppg2 = map(int, parts)
                            self.timestamps.append(timestamp)
                            self.ppg1_data.append(ppg1)
                            self.ppg2_data.append(ppg2)
                    except ValueError:
                        pass  # Skip invalid data lines
        
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        except serial.SerialException as e:
            print(f"Serial communication error: {e}")
        finally:
            if self.ser:
                self.ser.close()
                print("Serial connection closed")
                
                # Create a final summary plot if we have data
                if self.all_ptt_values:
                    self.create_summary_plot()

    def create_summary_plot(self):
        """Create a summary plot of all PTT data collected during the session"""
        if not self.all_ptt_values:
            return
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        fig.suptitle('PTT Analysis - Session Summary', fontsize=16)
        
        # Plot all PTT values
        ax1.plot(self.all_ptt_values, 'g-', label='All PTT Values')
        ax1.axhline(y=np.mean(self.all_ptt_values), color='r', linestyle='--', 
                   label=f'Mean: {np.mean(self.all_ptt_values):.2f} ms')
        ax1.set_title(f'All PTT Values ({len(self.all_ptt_values)} measurements)')
        ax1.set_xlabel('Measurement Number')
        ax1.set_ylabel('PTT (ms)')
        ax1.legend()
        
        # Plot histogram of PTT values
        ax2.hist(self.all_ptt_values, bins=20, color='blue', alpha=0.7)
        ax2.axvline(x=np.mean(self.all_ptt_values), color='r', linestyle='--',
                   label=f'Mean: {np.mean(self.all_ptt_values):.2f} ms')
        ax2.set_title('PTT Distribution')
        ax2.set_xlabel('PTT (ms)')
        ax2.set_ylabel('Frequency')
        ax2.legend()
        
        # Add statistics text
        stats_text = (
            f"Session Summary Statistics:\n"
            f"Total Collections: {self.collection_count}\n"
            f"Total PTT Measurements: {len(self.all_ptt_values)}\n"
            f"Average PTT: {np.mean(self.all_ptt_values):.2f} ms\n"
            f"Standard Deviation: {np.std(self.all_ptt_values):.2f} ms\n"
            f"Min PTT: {min(self.all_ptt_values):.2f} ms\n"
            f"Max PTT: {max(self.all_ptt_values):.2f} ms"
        )
        fig.text(0.1, 0.01, stats_text, fontsize=10)
        
        plt.tight_layout(rect=[0, 0.07, 1, 0.95])
        
        # Save the summary figure
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_folder, f"session_summary_{timestamp_str}.png")
        plt.savefig(filename, dpi=300)
        plt.close(fig)
        print(f"Session summary plot saved to: {filename}")

    def run(self):
        """Main execution function"""
        print("PTT Calculator - Using two PPG sensors with Arduino MKRZero")
        print("Plots will be saved to folder instead of displayed in real-time")
        
        if self.connect_to_arduino():
            # Start data collection
            self.collect_data()
        else:
            print("Failed to connect to Arduino. Exiting.")

if __name__ == "__main__":
    calculator = PTTCalculator()
    calculator.run()

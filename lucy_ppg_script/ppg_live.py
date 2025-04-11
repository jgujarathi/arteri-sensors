import serial
import matplotlib.pyplot as plt
import argparse
import datetime
import os
import time
import threading
import csv
from matplotlib.animation import FuncAnimation

# Global variables for data
timestamps = []
sensor1_values = []
sensor2_values = []
recording = True
csv_writer = None
csv_file = None

def read_serial_data(ser, csv_path):
    """Thread function to continuously read data from serial port"""
    global timestamps, sensor1_values, sensor2_values, recording, csv_writer, csv_file
    
    # Create and open CSV file
    csv_file = open(csv_path, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["timestamp", "sensor1", "sensor2"])
    
    print("Reading data from Arduino...")
    
    try:
        while recording:
            line = ser.readline().decode('utf-8').strip()
            
            # Parse data (timestamp,sensor1,sensor2)
            try:
                parts = line.split(',')
                if len(parts) == 3:
                    timestamp, sensor1, sensor2 = map(int, parts)
                    
                    # Add to global data lists
                    timestamps.append(timestamp)
                    sensor1_values.append(sensor1)
                    sensor2_values.append(sensor2)
                    
                    # Write to CSV file
                    csv_writer.writerow([timestamp, sensor1, sensor2])
            except ValueError:
                # Skip lines that can't be parsed
                pass
    except Exception as e:
        print(f"Error in serial reading thread: {e}")
    finally:
        if csv_file and not csv_file.closed:
            csv_file.close()
            print(f"CSV file closed")

def update_plot(frame, line1, line2, ax):
    """Update function for animation"""
    # Update line data
    if len(timestamps) > 0:
        # Only show the last 500 points for better visualization
        display_limit = 500
        
        if len(timestamps) <= display_limit:
            x_data = timestamps
            y1_data = sensor1_values
            y2_data = sensor2_values
        else:
            x_data = timestamps[-display_limit:]
            y1_data = sensor1_values[-display_limit:]
            y2_data = sensor2_values[-display_limit:]
        
        line1.set_data(x_data, y1_data)
        line2.set_data(x_data, y2_data)
        
        # Adjust x-axis limit to show only recent data
        ax.set_xlim(min(x_data), max(x_data))
        
        # Adjust y-axis limits if needed
        all_y = y1_data + y2_data
        if all_y:
            y_min = min(all_y) - 50
            y_max = max(all_y) + 50
            ax.set_ylim(y_min, y_max)
    
    return line1, line2

def main():
    global recording
    
    parser = argparse.ArgumentParser(description='Record PPG data with live plot')
    parser.add_argument('--port', type=str, required=True, help='Serial port (e.g., COM3 on Windows or /dev/ttyUSB0 on Linux/Mac)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--output', type=str, default='ppg_data', help='Output filename prefix (without extension)')
    args = parser.parse_args()
    
    # Generate timestamp for filenames
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"{args.output}_{timestamp_str}.csv"
    png_path = f"{args.output}_{timestamp_str}.png"
    
    try:
        # Connect to Arduino
        ser = serial.Serial(args.port, args.baud, timeout=1)
        print(f"Connected to {args.port} at {args.baud} baud")
        time.sleep(2)  # Allow time for Arduino to reset
        
        # Wait for start signal
        print("Waiting for Arduino to start data collection...")
        while True:
            line = ser.readline().decode('utf-8').strip()
            if line == "START_RECORDING":
                print("Data collection started")
                break
        
        # Start serial reading thread
        serial_thread = threading.Thread(target=read_serial_data, args=(ser, csv_path))
        serial_thread.daemon = True
        serial_thread.start()
        
        # Set up the plot
        plt.ion()  # Enable interactive mode
        fig, ax = plt.subplots(figsize=(12, 6))
        line1, = ax.plot([], [], label='Sensor 1 (A1)')
        line2, = ax.plot([], [], label='Sensor 2 (A2)')
        
        ax.set_title('PPG Sensor Readings (Live)')
        ax.set_xlabel('Time (milliseconds)')
        ax.set_ylabel('Analog Reading')
        ax.legend()
        ax.grid(True)
        
        # Set up the animation
        ani = FuncAnimation(fig, update_plot, fargs=(line1, line2, ax), 
                          interval=100, blit=True)
        
        print("Live plotting started. Press Ctrl+C to stop recording.")
        print(f"Data is being saved to {csv_path}")
        print("Plot will be saved upon exit.")
        
        # Show the plot (this will block until the plot window is closed)
        plt.show()
        
        # Handle user termination
        try:
            while True:
                plt.pause(0.1)  # Small pause to allow GUI to update
        except KeyboardInterrupt:
            print("\nRecording stopped by user")
        
    except serial.SerialException as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Clean up
        recording = False
        
        # Wait for serial thread to finish
        if 'serial_thread' in locals() and serial_thread.is_alive():
            serial_thread.join(timeout=1.0)
        
        # Close the serial connection if it's open
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")
        
        # Save the final plot
        if len(timestamps) > 0:
            plt.figure(figsize=(12, 6))
            plt.plot(timestamps, sensor1_values, label='Sensor 1 (A1)')
            plt.plot(timestamps, sensor2_values, label='Sensor 2 (A2)')
            plt.title('PPG Sensor Readings')
            plt.xlabel('Time (milliseconds)')
            plt.ylabel('Analog Reading')
            plt.legend()
            plt.grid(True)
            plt.savefig(png_path)
            print(f"Final plot saved as {png_path}")

if __name__ == "__main__":
    main()

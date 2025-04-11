import serial
import matplotlib.pyplot as plt
import argparse
import datetime
import os
import time

def main():
    parser = argparse.ArgumentParser(description='Record PPG data and save plot as image')
    parser.add_argument('--port', type=str, required=True, help='Serial port (e.g., COM3 on Windows or /dev/ttyUSB0 on Linux/Mac)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--output', type=str, default='ppg_plot', help='Output filename prefix (without extension)')
    args = parser.parse_args()
    
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
        
        # Collect data
        timestamps = []
        sensor1_values = []
        sensor2_values = []
        
        print("Recording data...")
        while True:
            line = ser.readline().decode('utf-8').strip()
            
            # Check for end signal
            if line == "END_RECORDING":
                print("Data collection completed")
                break
                
            # Parse data (timestamp,sensor1,sensor2)
            try:
                parts = line.split(',')
                if len(parts) == 3:
                    timestamp, sensor1, sensor2 = map(int, parts)
                    timestamps.append(timestamp)
                    sensor1_values.append(sensor1)
                    sensor2_values.append(sensor2)
            except ValueError:
                # Skip lines that can't be parsed
                pass
        
        # Create plot
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, sensor1_values, label='Sensor 1 (A1)')
        plt.plot(timestamps, sensor2_values, label='Sensor 2 (A2)')
        
        plt.title('PPG Sensor Readings')
        plt.xlabel('Time (milliseconds)')
        plt.ylabel('Analog Reading')
        plt.legend()
        plt.grid(True)
        
        # Add timestamp to filename
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.output}_{timestamp_str}"
        
        # Save as PNG
        png_path = f"{filename}.png"
        plt.savefig(png_path)
        print(f"Plot saved as {png_path}")
        
        # Save raw data as CSV
        csv_path = f"{filename}.csv"
        with open(csv_path, 'w') as f:
            f.write("timestamp,sensor1,sensor2\n")
            for i in range(len(timestamps)):
                f.write(f"{timestamps[i]},{sensor1_values[i]},{sensor2_values[i]}\n")
        print(f"Raw data saved as {csv_path}")
        
        # Display the plot
        plt.show()
        
    except serial.SerialException as e:
        print(f"Error: {e}")
    finally:
        # Close the serial connection if it's open
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    main()

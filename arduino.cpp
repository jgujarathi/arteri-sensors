/*
 * Playground Pulse PPG Sensor Data Collection for PTT Calculation
 * For Arduino MKRZero
 * 
 * This script collects data from two PPG sensors for 10 seconds every minute
 * and sends the data via USB serial to a laptop for PTT calculation.
 */

// Pin definitions for the PPG sensors
const int PPG_SENSOR_1 = A0;  // First PPG sensor on analog pin A0
const int PPG_SENSOR_2 = A1;  // Second PPG sensor on analog pin A1

// Timing constants
const unsigned long SAMPLE_PERIOD_MS = 10;     // Sample every 10ms (100Hz sample rate)
const unsigned long COLLECTION_TIME_MS = 10000; // Collect for 10 seconds
const unsigned long WAIT_TIME_MS = 50000;      // Wait for 50 seconds (60 seconds total cycle)

// Buffer for timestamp and sensor values
unsigned long timestamp;
int sensor1Value;
int sensor2Value;

void setup() {
  // Initialize serial communication at 115200 baud
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  
  // Configure analog read resolution (MKRZero supports 12-bit resolution)
  analogReadResolution(12);
  
  Serial.println("PPG PTT Data Collection System");
  Serial.println("Collecting data for 10 seconds every minute");
}

void loop() {
  // Signal the start of data collection
  Serial.println("START_DATA_COLLECTION");
  
  unsigned long startTime = millis();
  unsigned long endTime = startTime + COLLECTION_TIME_MS;
  
  // Collect data for 10 seconds
  while (millis() < endTime) {
    // Get timestamp (milliseconds since start of collection)
    timestamp = millis() - startTime;
    
    // Read values from both sensors
    sensor1Value = analogRead(PPG_SENSOR_1);
    sensor2Value = analogRead(PPG_SENSOR_2);
    
    // Send data in CSV format: timestamp,sensor1,sensor2
    Serial.print(timestamp);
    Serial.print(",");
    Serial.print(sensor1Value);
    Serial.print(",");
    Serial.println(sensor2Value);
    
    // Wait for the next sample period
    delay(SAMPLE_PERIOD_MS);
  }
  
  // Signal the end of data collection
  Serial.println("END_DATA_COLLECTION");
  
  // Wait for the remaining time in the minute
  delay(WAIT_TIME_MS);
}

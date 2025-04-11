const int SENSOR_PINS[] = {A1, A2};  // Use A1 and A2 pins instead of D0 and D1
const int LED_PIN = 32;              // Built-in LED on pin 32
const unsigned long DURATION = 10000; // Run for 10 seconds (in milliseconds)

void setup() {
  Serial.begin(115200);
  while (!Serial);  // Wait for serial connection
  
  // Configure A1 and A2 as inputs
  for (int i = 0; i < 2; i++) {
    pinMode(SENSOR_PINS[i], INPUT);
    digitalWrite(SENSOR_PINS[i], LOW);  // Disable pullup
  }
  
  pinMode(LED_PIN, OUTPUT);
  
  // Signal start of data collection
  Serial.println("START_RECORDING");
}

void loop() {
  static unsigned long startTime = millis();  // Record the starting time
  
  // Stop after DURATION (10 seconds)
  if (millis() - startTime >= DURATION) {
    // Signal end of data collection
    Serial.println("END_RECORDING");
    Serial.println("10 seconds elapsed. Stopping...");
    while (1);  // Stop execution by entering an infinite loop
  }
  
  // Read analog values from A1 and A2
  int sensor1 = analogRead(SENSOR_PINS[0]);
  int sensor2 = analogRead(SENSOR_PINS[1]);
  
  // Send timestamp along with sensor values
  unsigned long timestamp = millis() - startTime;
  Serial.print(timestamp);
  Serial.print(",");
  Serial.print(sensor1);
  Serial.print(",");
  Serial.println(sensor2);
  
  // Blink LED to indicate activity
  digitalWrite(LED_PIN, HIGH);
  delay(50);
  digitalWrite(LED_PIN, LOW);
}

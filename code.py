#include <humblecoder-project-1_inferencing.h>

/* * FINAL MODULE 1: Wireless Web Server Monitor
 * ------------------------------------------------
 * 1. Connects to Wi-Fi
 * 2. Runs AI Inference
 * 3. Hosts a webpage you can view on your laptop
 */

#include <WiFi.h>
#include <WebServer.h>
#include "DHT.h"

// --- STEP 1: WI-FI SETUP ---
const char* ssid     = "NSUT-Campus";
const char* password = "";

// --- STEP 2: LIBRARY SETUP ---#include <Your_Project_Name_Inferencing.h> 

// --- STEP 3: PINS ---
#define DHTPIN 4
#define DHTTYPE DHT11
#define GAS_PIN 34

DHT dht(DHTPIN, DHTTYPE);
WebServer server(80); // Create a web server on port 80

// Global variables to store latest results for the website
float features[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE];
String currentStatus = "Waiting...";
float currentGas = 0;
float currentProb = 0;
String statusColor = "black";

// HTML Code for the webpage
void handleRoot() {
  String html = "<!DOCTYPE html><html>";
  html += "<head><meta http-equiv='refresh' content='3'>"; // Auto-refresh every 3 sec
  html += "<style>body{font-family: sans-serif; text-align: center; margin-top: 50px;}";
  html += "h1{font-size: 50px;} .value{font-size: 30px; color: #555;}</style></head>";
  html += "<body>";
  html += "<h2>Air Quality Monitor</h2>";
  
  // Dynamic Content
  html += "<h1 style='color:" + statusColor + ";'>" + currentStatus + "</h1>";
  html += "<p class='value'>Gas Level: " + String(currentGas, 0) + "</p>";
  html += "<p class='value'>Danger Confidence: " + String(currentProb * 100, 1) + "%</p>";
  
  html += "<p><em>Refreshing automatically...</em></p>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
}

void setup() {
    Serial.begin(115200);
    dht.begin();
    pinMode(GAS_PIN, INPUT);

    // Connect to Wi-Fi
    Serial.print("Connecting to Wi-Fi");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWi-Fi Connected!");
    Serial.print("GO TO THIS URL: http://");
    Serial.println(WiFi.localIP());

    // Start Web Server
    server.on("/", handleRoot);
    server.begin();
    Serial.println("Web server started");
    
    // Warmup
    delay(2000);
}

void loop() {
    // 1. Handle Web Client (Check if someone is looking at the page)
    server.handleClient();

    // 2. Buffer Data (Silent)
    for (size_t ix = 0; ix < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE; ix += 3) {
        float gas = analogRead(GAS_PIN);
        float hum = dht.readHumidity();
        float temp = dht.readTemperature();
        
        if (isnan(hum)) hum = 0; if (isnan(temp)) temp = 0;

        features[ix] = gas;
        features[ix+1] = temp;
        features[ix+2] = hum;
        
        // IMPORTANT: Frequent calls to handleClient keep the website responsive
        // even while collecting data!
        delay(EI_CLASSIFIER_INTERVAL_MS); 
    }

    // 3. Run Inference
    ei_impulse_result_t result = { 0 };
    signal_t signal;
    numpy::signal_from_buffer(features, EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE, &signal);
    run_classifier(&signal, &result, false);

    // 4. Update Global Variables (So the website sees new data)
    currentGas = features[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE - 3];
    
    // Find Danger Score
    float danger_score = 0;
    for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
        if (strcmp(result.classification[ix].label, "danger") == 0) {
            danger_score = result.classification[ix].value;
        }
    }
    currentProb = danger_score;

    // 5. Decide Status
    if (danger_score > 0.7) {
        currentStatus = "DANGER !!!";
        statusColor = "red";
    } else {
        currentStatus = "SAFE";
        statusColor = "green";
    }
    
    // Debug print (optional)
    Serial.println("Updated: " + currentStatus);
}

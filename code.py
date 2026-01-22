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
  String html = "<!DOCTYPE html><html lang='en'>";
  html += "<head>";
  html += "<meta charset='UTF-8'>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<meta http-equiv='refresh' content='3'>";
  html += "<title>Smart Air Quality Monitor</title>";

  html += "<style>";
  html += "body{margin:0;font-family:'Segoe UI',sans-serif;background:#f4f6f8;}";
  html += ".container{max-width:900px;margin:auto;padding:20px;}";
  html += "h1{text-align:center;margin-bottom:10px;}";
  html += ".status{padding:30px;border-radius:15px;color:white;text-align:center;font-size:42px;font-weight:bold;}";
  html += ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-top:30px;}";
  html += ".card{background:white;padding:20px;border-radius:15px;box-shadow:0 8px 20px rgba(0,0,0,0.08);}";
  html += ".label{font-size:14px;color:#888;}";
  html += ".value{font-size:34px;font-weight:bold;margin-top:5px;}";
  html += ".footer{text-align:center;margin-top:30px;color:#777;font-size:14px;}";
  html += "</style>";
  html += "</head>";

  html += "<body>";
  html += "<div class='container'>";
  html += "<h1>🌍 Smart Air Quality Monitor</h1>";

  html += "<div class='status' style='background:" + statusColor + ";'>";
  html += currentStatus;
  html += "</div>";

  html += "<div class='grid'>";

  html += "<div class='card'><div class='label'>🧪 Gas Level</div>";
  html += "<div class='value'>" + String(currentGas, 0) + "</div></div>";

  html += "<div class='card'><div class='label'>🌡 Temperature</div>";
  html += "<div class='value'>" + String(dht.readTemperature(), 1) + " °C</div></div>";

  html += "<div class='card'><div class='label'>💧 Humidity</div>";
  html += "<div class='value'>" + String(dht.readHumidity(), 1) + " %</div></div>";

  html += "<div class='card'><div class='label'>🧠 Danger Confidence</div>";
  html += "<div class='value'>" + String(currentProb * 100, 1) + " %</div></div>";

  html += "</div>";

  html += "<div class='footer'>";
  html += "Auto-refresh every 3 seconds • Edge AI Powered";
  html += "</div>";

  html += "</div></body></html>";

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

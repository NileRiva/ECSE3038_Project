#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "env.h"

const char* putendpoint = API_URL_PUT;
const char* getendpoint = API_URL_GET;

const int fanpin = 22;
const int lightpin = 23;

float float_rand(float min,float max)
{
    float scale = rand() / (float) RAND_MAX; /* [0, 1.0] */
    return min + scale * ( max - min );      /* [min, max] */
}

void setup() {
  Serial.begin(9600);
  pinMode(fanpin, OUTPUT);
  pinMode(lightpin, OUTPUT);

  WiFi.begin(WIFI_USER, WIFI_PASS);
  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("The Bluetooth Device is Ready to Pair");
  Serial.println("Connected @");
  Serial.print(WiFi.localIP());
}


void loop() {
//PUT Request
  if(WiFi.status()== WL_CONNECTED){   
    
    HTTPClient http;
    String http_response;

    //PUT REQUEST
    http.begin(putendpoint);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<1024> putdoc; // Empty JSONDocument
    String httpRequestData; // Emtpy string to be used to store HTTP request data string

    putdoc["temperature"]=float_rand(21.0,33.0);
    serializeJson(putdoc, httpRequestData);

    int PUTResponseCode = http.PUT(httpRequestData);


    if (PUTResponseCode>0) {
        Serial.print("Response:");
        Serial.print(PUTResponseCode);}

    else {
        Serial.print("Error: ");
        Serial.println(PUTResponseCode);}
      
      http.end();
      
    //GET REQUEST
    http.begin(getendpoint);
  

    int httpResponseCode = http.GET();


    if (httpResponseCode>0) {
        Serial.print("Response:");
        Serial.print(httpResponseCode);
        http_response = http.getString();
        Serial.println(http_response);}
      else {
        Serial.print("Error: ");
        Serial.println(httpResponseCode);}
      http.end();

      
      StaticJsonDocument<1024> doc;
      DeserializationError error = deserializeJson(doc, http_response);

      if (error) 
      { Serial.print("deserializeJson() failed:");
        Serial.println(error.c_str());
        return;}
      
      bool lightstate = doc["light"];
      bool fanstate = doc["fan"];
  
  
      Serial.println("Light:");
      Serial.println(lightstate);
      Serial.println("Fan:");
      Serial.println(fanstate);

      digitalWrite(fanpin, fanstate);
      digitalWrite(lightpin,lightstate);
      
      Serial.println("Light and Fan Switched Successfully");
      
      delay(1000);   
  }
  
  else {Serial.println("Not Connected");}

}
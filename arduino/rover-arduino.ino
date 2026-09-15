// ============================================================
// rover_arduino.ino
// Adafruit Motor Shield V1 + AFMotor
// Modes: MANUAL (GUI drive) | AUTONOMOUS (obstacle avoidance)
// Sensors: Front A2/A3  Left A4/A5  Right A0/A1
// ============================================================

#include <AFMotor.h>
#include <ArduinoJson.h>

// ============================================================
// MOTORS
//        FRONT
//   M1 (FL)      M2 (FR)
//   M3 (RL)      M4 (RR)
//        BACK
// ============================================================

AF_DCMotor motorFL(1);
AF_DCMotor motorFR(2);
AF_DCMotor motorRL(3);
AF_DCMotor motorRR(4);

// ============================================================
// ULTRASONIC PINS
// ============================================================

#define TRIG_F  A2
#define ECHO_F  A3
#define TRIG_L  A4
#define ECHO_L  A5
#define TRIG_R  A0
#define ECHO_R  A1

// ============================================================
// TUNING
// ============================================================

#define DANGER_CM           15
#define SPEED               255
#define SIDE_SLOW           20
#define BACK_TIME           5500
#define STEER_TIME          5500
#define SENSOR_INTERVAL_MS  80     // send sensors every 80 ms
#define COMMAND_TIMEOUT_MS  600    // watchdog for manual mode

// ============================================================
// STATE
// ============================================================

bool autonomousMode   = false;
bool obstacleAvoid    = false;   // can be toggled independently in manual
unsigned long lastCommandTime = 0;
unsigned long lastSensorTime  = 0;

// ============================================================
// SENSOR READ
// ============================================================

long getDistance(int trig, int echo) {
    digitalWrite(trig, LOW);
    delayMicroseconds(4);
    digitalWrite(trig, HIGH);
    delayMicroseconds(10);
    digitalWrite(trig, LOW);
    long dur = pulseIn(echo, HIGH, 35000);
    if (dur == 0) return 999;
    return dur * 0.034 / 2;
}

// ============================================================
// MOTOR HELPERS
// ============================================================

void setLeft(int speed) {
    speed = constrain(speed, -255, 255);
    uint8_t pwm = abs(speed);
    if (speed > 0) {
        motorFL.setSpeed(pwm); motorFL.run(FORWARD);
        motorRL.setSpeed(pwm); motorRL.run(FORWARD);
    } else if (speed < 0) {
        motorFL.setSpeed(pwm); motorFL.run(BACKWARD);
        motorRL.setSpeed(pwm); motorRL.run(BACKWARD);
    } else {
        motorFL.run(RELEASE); motorRL.run(RELEASE);
    }
}

void setRight(int speed) {
    speed = constrain(speed, -255, 255);
    uint8_t pwm = abs(speed);
    if (speed > 0) {
        motorFR.setSpeed(pwm); motorFR.run(FORWARD);
        motorRR.setSpeed(pwm); motorRR.run(FORWARD);
    } else if (speed < 0) {
        motorFR.setSpeed(pwm); motorFR.run(BACKWARD);
        motorRR.setSpeed(pwm); motorRR.run(BACKWARD);
    } else {
        motorFR.run(RELEASE); motorRR.run(RELEASE);
    }
}

void stopAll() {
    motorFL.run(RELEASE); motorRL.run(RELEASE);
    motorFR.run(RELEASE); motorRR.run(RELEASE);
}

void goForward() {
    motorFL.setSpeed(SPEED); motorFL.run(FORWARD);
    motorFR.setSpeed(SPEED); motorFR.run(FORWARD);
    motorRL.setSpeed(SPEED); motorRL.run(FORWARD);
    motorRR.setSpeed(SPEED); motorRR.run(FORWARD);
}

void goBackward() {
    motorFL.setSpeed(SPEED); motorFL.run(BACKWARD);
    motorFR.setSpeed(SPEED); motorFR.run(BACKWARD);
    motorRL.setSpeed(SPEED); motorRL.run(BACKWARD);
    motorRR.setSpeed(SPEED); motorRR.run(BACKWARD);
}

void curveLeft() {
    motorFL.setSpeed(SIDE_SLOW); motorFL.run(FORWARD);
    motorRL.setSpeed(SIDE_SLOW); motorRL.run(FORWARD);
    motorFR.setSpeed(SPEED);     motorFR.run(FORWARD);
    motorRR.setSpeed(SPEED);     motorRR.run(FORWARD);
}

void curveRight() {
    motorFL.setSpeed(SPEED);     motorFL.run(FORWARD);
    motorRL.setSpeed(SPEED);     motorRL.run(FORWARD);
    motorFR.setSpeed(SIDE_SLOW); motorFR.run(FORWARD);
    motorRR.setSpeed(SIDE_SLOW); motorRR.run(FORWARD);
}

void applyDrive(int vx, int vy) {
    vx = constrain(vx, -100, 100);
    vy = constrain(vy, -100, 100);
    int left  = constrain(vy + vx, -100, 100);
    int right = constrain(vy - vx, -100, 100);
    setLeft(map(left,  -100, 100, -255, 255));
    setRight(map(right, -100, 100, -255, 255));
}

// ============================================================
// SEND SENSOR JSON
// ============================================================

void sendSensors(long f, long r, long l) {
    // Format: {"type":"sensors","front":xx,"right":xx,"left":xx}
    Serial.print("{\"type\":\"sensors\",\"front\":");
    Serial.print(f == 999 ? -1 : f);
    Serial.print(",\"right\":");
    Serial.print(r == 999 ? -1 : r);
    Serial.print(",\"left\":");
    Serial.print(l == 999 ? -1 : l);
    Serial.println("}");
}

// ============================================================
// AUTONOMOUS AVOID
// ============================================================

void avoidFront(long distR, long distL) {
    Serial.println(">>> FRONT BLOCKED — STOP");
    stopAll();
    delay(200);

    Serial.println(">>> REVERSING...");
    goBackward();
    delay(BACK_TIME);
    stopAll();
    delay(300);

    Serial.println(">>> CURVING RIGHT (forced)");
    curveRight();
    delay(STEER_TIME);
    stopAll();
    delay(200);

    Serial.println(">>> RESUME FORWARD");
}

void runAutonomous() {
    long distF = getDistance(TRIG_F, ECHO_F);
    long distR = getDistance(TRIG_R, ECHO_R);
    long distL = getDistance(TRIG_L, ECHO_L);

    Serial.print("[F:"); Serial.print(distF);
    Serial.print(" R:"); Serial.print(distR);
    Serial.print(" L:"); Serial.print(distL);
    Serial.println("]");

    // Send sensors to GUI
    unsigned long now = millis();
    if (now - lastSensorTime >= SENSOR_INTERVAL_MS) {
        lastSensorTime = now;
        sendSensors(distF, distR, distL);
    }

    if (distF < DANGER_CM) {
        avoidFront(distR, distL);
    } else if (distR < DANGER_CM && distL < DANGER_CM) {
        goForward();
    } else if (distR < DANGER_CM) {
        curveLeft();
    } else if (distL < DANGER_CM) {
        curveRight();
    } else {
        goForward();
    }
}

// ============================================================
// PROCESS COMMAND (manual mode)
// ============================================================

void processCommand(const String &line) {
    StaticJsonDocument<128> doc;
    if (deserializeJson(doc, line) != DeserializationError::Ok) {
        Serial.println("{\"type\":\"error\",\"message\":\"invalid_json\"}");
        return;
    }

    const char *type = doc["type"];
    if (!type) return;

    if (strcmp(type, "drive") == 0) {
        int vx = constrain((int)(doc["vx"] | 0), -100, 100);
        int vy = constrain((int)(doc["vy"] | 0), -100, 100);
        applyDrive(vx, vy);
        lastCommandTime = millis();

    } else if (strcmp(type, "stop") == 0) {
        stopAll();
        lastCommandTime = millis();

    } else if (strcmp(type, "mode") == 0) {
        const char *m = doc["mode"];
        if (m && strcmp(m, "autonomous") == 0) {
            autonomousMode = true;
            obstacleAvoid  = true;
            stopAll();
            Serial.println("{\"type\":\"mode_ack\",\"mode\":\"autonomous\"}");
        } else {
            autonomousMode = false;
            obstacleAvoid  = false;
            stopAll();
            lastCommandTime = millis();
            Serial.println("{\"type\":\"mode_ack\",\"mode\":\"manual\"}");
        }

    } else if (strcmp(type, "obstacle") == 0) {
        obstacleAvoid = (bool)(doc["enabled"] | false);
        Serial.print("{\"type\":\"obstacle_ack\",\"enabled\":");
        Serial.print(obstacleAvoid ? "true" : "false");
        Serial.println("}");
    }
}

// ============================================================
// SETUP
// ============================================================

void setup() {
    Serial.begin(115200);

    pinMode(TRIG_F, OUTPUT); pinMode(ECHO_F, INPUT);
    pinMode(TRIG_R, OUTPUT); pinMode(ECHO_R, INPUT);
    pinMode(TRIG_L, OUTPUT); pinMode(ECHO_L, INPUT);

    stopAll();
    lastCommandTime = millis();
    lastSensorTime  = millis();

    Serial.println("{\"type\":\"arduino_ready\"}");
}

// ============================================================
// LOOP
// ============================================================

void loop() {
    // ---- Read serial commands ----
    static String lineBuffer = "";
    while (Serial.available() > 0) {
        char c = Serial.read();
        if (c == '\n') {
            lineBuffer.trim();
            if (lineBuffer.length() > 0) {
                processCommand(lineBuffer);
            }
            lineBuffer = "";
        } else if (c != '\r') {
            lineBuffer += c;
            if (lineBuffer.length() > 200) lineBuffer = "";
        }
    }

    // ---- Autonomous mode ----
    if (autonomousMode) {
        runAutonomous();
        delay(40);
        return;
    }

    // ---- Manual mode — send sensors periodically ----
    unsigned long now = millis();
    if (now - lastSensorTime >= SENSOR_INTERVAL_MS) {
        lastSensorTime = now;
        long distF = getDistance(TRIG_F, ECHO_F);
        long distR = getDistance(TRIG_R, ECHO_R);
        long distL = getDistance(TRIG_L, ECHO_L);
        sendSensors(distF, distR, distL);

        // Obstacle avoidance in manual mode
        if (obstacleAvoid) {
            if (distF < DANGER_CM) {
                stopAll();
                lastCommandTime = millis(); // reset watchdog
            } else if (distR < DANGER_CM) {
                curveLeft();
                lastCommandTime = millis();
            } else if (distL < DANGER_CM) {
                curveRight();
                lastCommandTime = millis();
            }
        }
    }

    // ---- Watchdog ----
    if (millis() - lastCommandTime > COMMAND_TIMEOUT_MS) {
        stopAll();
    }
}

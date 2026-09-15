#!/usr/bin/env python3

import socket
import serial
import threading
import time
import json


# ============================================================
# SETTINGS
# ============================================================

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000

SERIAL_PORT = "/dev/ttyACM0"
# For CH340:
# SERIAL_PORT = "/dev/ttyUSB0"

BAUD = 115200

# No TCP timeout — Arduino watchdog (500 ms) handles safety stops.
# A short TCP timeout here was dropping the client mid-session.


# ============================================================
# GLOBALS
# ============================================================

ser = None

serial_lock = threading.Lock()

client = None

client_lock = threading.Lock()

arduino_online = False


# ============================================================
# SEND TO LAPTOP
# ============================================================

def send_to_laptop(obj):

    global client

    with client_lock:

        if client is None:
            return False

        try:

            message = (
                json.dumps(obj)
                + "\n"
            )

            client.sendall(
                message.encode()
            )

            return True

        except Exception:

            return False


# ============================================================
# SEND TO ARDUINO
# ============================================================

def send_to_arduino(obj):

    global ser

    with serial_lock:

        if ser is None:
            return False

        try:

            if not ser.is_open:
                return False

            message = (
                json.dumps(obj)
                + "\n"
            )

            ser.write(
                message.encode()
            )

            ser.flush()

            print(
                f"[ARDUINO TX] {message.strip()}"
            )

            return True

        except Exception as error:

            print(
                f"Arduino send error: {error}"
            )

            return False


# ============================================================
# OPEN ARDUINO
# ============================================================

def open_arduino():

    global ser
    global arduino_online

    while True:

        try:

            print(
                f"Connecting Arduino: "
                f"{SERIAL_PORT}"
            )

            new_serial = serial.Serial(
                SERIAL_PORT,
                BAUD,
                timeout=0.1
            )

            time.sleep(2)

            with serial_lock:
                ser = new_serial

            print(
                "Arduino serial connected"
            )

            arduino_online = False

            return

        except Exception as error:

            print(
                f"Arduino connection failed: "
                f"{error}"
            )

            time.sleep(3)


# ============================================================
# CLOSE ARDUINO
# ============================================================

def close_arduino():

    global ser
    global arduino_online

    try:

        send_to_arduino(
            {
                "type": "stop"
            }
        )

    except Exception:
        pass

    with serial_lock:

        if ser:

            try:
                ser.close()

            except Exception:
                pass

        ser = None

    if arduino_online:

        arduino_online = False

        send_to_laptop(
            {
                "type": "rover_status",
                "online": False
            }
        )


# ============================================================
# ARDUINO READER
# ============================================================

def arduino_reader():

    global arduino_online

    buffer = b""

    while True:

        try:

            if ser is None:

                time.sleep(0.5)

                continue

            if not ser.is_open:

                close_arduino()

                open_arduino()

                continue


            if ser.in_waiting:

                data = ser.read(
                    ser.in_waiting
                )

            else:

                data = ser.read(1)


            if not data:

                continue


            buffer += data


            while b"\n" in buffer:

                line, buffer = buffer.split(
                    b"\n",
                    1
                )

                line = line.strip()

                if not line:
                    continue


                try:

                    obj = json.loads(
                        line.decode(
                            errors="ignore"
                        )
                    )

                except Exception:

                    print(
                        f"Bad Arduino JSON: "
                        f"{line}"
                    )

                    continue

                print(
                    f"[ARDUINO RX] "
                    f"{line.decode(errors='ignore')}"
                )


                msg_type = obj.get(
                    "type"
                )


                # ------------------------------------------------
                # ARDUINO READY
                # ------------------------------------------------

                if msg_type == "arduino_ready":

                    arduino_online = True

                    print(
                        "Arduino READY"
                    )

                    send_to_laptop(
                        {
                            "type":
                            "rover_status",
                            "online":
                            True
                        }
                    )


                # ------------------------------------------------
                # SENSOR DATA — attach Pi timestamp before forwarding
                # ------------------------------------------------

                elif msg_type == "sensors":

                    obj["ts"] = time.time()

                    send_to_laptop(
                        obj
                    )


                # ------------------------------------------------
                # ERROR
                # ------------------------------------------------

                elif msg_type == "error":

                    print(
                        f"Arduino error: "
                        f"{obj}"
                    )

                    send_to_laptop(
                        obj
                    )


        except Exception as error:

            print(
                f"Arduino reader error: "
                f"{error}"
            )

            close_arduino()

            time.sleep(1)

            open_arduino()


# ============================================================
# HANDLE LAPTOP
# ============================================================

def handle_laptop(sock, address):

    global client

    print(
        f"Laptop connected: "
        f"{address[0]}"
    )

    with client_lock:

        client = sock


    buffer = ""


    try:

        while True:

            data = sock.recv(
                4096
            )


            if not data:

                break


            buffer += data.decode(
                errors="ignore"
            )


            while "\n" in buffer:

                line, buffer = buffer.split(
                    "\n",
                    1
                )

                line = line.strip()


                if not line:

                    continue


                try:

                    obj = json.loads(
                        line
                    )

                except Exception:

                    print(
                        f"Bad laptop JSON: "
                        f"{line}"
                    )

                    continue


                msg_type = obj.get(
                    "type"
                )


                # ------------------------------------------------
                # HELLO
                # ------------------------------------------------

                if msg_type == "hello":

                    sock.sendall(
                        (
                            json.dumps(
                                {
                                    "type":
                                    "hello_ack"
                                }
                            )
                            + "\n"
                        ).encode()
                    )

                    # Tell GUI current Arduino state

                    send_to_laptop(
                        {
                            "type":
                            "rover_status",
                            "online":
                            arduino_online
                        }
                    )


                # ------------------------------------------------
                # DRIVE
                # ------------------------------------------------

                elif msg_type == "drive":

                    try:

                        vx = float(
                            obj.get(
                                "vx",
                                0
                            )
                        )

                        vy = float(
                            obj.get(
                                "vy",
                                0
                            )
                        )

                    except Exception:

                        continue


                    vx = max(
                        -100,
                        min(
                            100,
                            vx
                        )
                    )

                    vy = max(
                        -100,
                        min(
                            100,
                            vy
                        )
                    )


                    cmd = {
                        "type":
                        "drive",

                        "vx":
                        vx,

                        "vy":
                        vy
                    }

                    print(
                        f"[DRIVE] vx={vx:+.1f}  vy={vy:+.1f}"
                    )

                    send_to_arduino(cmd)


                # ------------------------------------------------
                # STOP
                # ------------------------------------------------

                elif msg_type == "stop":

                    print(
                        "[STOP]"
                    )

                    send_to_arduino(
                        {
                            "type":
                            "stop"
                        }
                    )


                # ------------------------------------------------
                # MODE
                # ------------------------------------------------

                elif msg_type == "mode":

                    send_to_arduino(
                        obj
                    )


                # ------------------------------------------------
                # OBSTACLE
                # ------------------------------------------------

                elif msg_type == "obstacle":

                    send_to_arduino(
                        obj
                    )


    except Exception as error:

        print(
            f"Laptop connection error: "
            f"{error}"
        )


    finally:

        # ========================================================
        # SAFETY STOP
        # ========================================================

        print(
            "Laptop disconnected -> STOP"
        )

        send_to_arduino(
            {
                "type":
                "stop"
            }
        )


        with client_lock:

            if client == sock:

                client = None


        try:

            sock.close()

        except Exception:
            pass


# ============================================================
# TCP SERVER
# ============================================================

def tcp_server():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(
        (
            SERVER_HOST,
            SERVER_PORT
        )
    )

    server.listen(1)

    print(
        "======================================"
    )

    print(
        "       ROVER RASPBERRY PI SERVER"
    )

    print(
        "======================================"
    )

    print(
        f"Listening on port {SERVER_PORT}"
    )

    print()

    while True:

        try:

            sock, address = server.accept()

            # Only allow one laptop

            with client_lock:

                old_client = client

            if old_client:

                try:

                    old_client.close()

                except Exception:
                    pass


            handle_laptop(
                sock,
                address
            )


        except Exception as error:

            print(
                f"Server error: {error}"
            )

            time.sleep(1)


# ============================================================
# SHOW IP
# ============================================================

def show_ip():

    try:

        hostname = socket.gethostname()

        addresses = socket.getaddrinfo(
            hostname,
            None
        )

        ips = set()

        for item in addresses:

            ip = item[4][0]

            if "." in ip:

                if not ip.startswith(
                    "127."
                ):

                    ips.add(ip)


        print(
            "Raspberry Pi IP address(es):"
        )

        for ip in sorted(ips):

            print(
                f"    {ip}"
            )

        print()

    except Exception:

        pass


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    show_ip()

    open_arduino()

    threading.Thread(
        target=arduino_reader,
        daemon=True
    ).start()

    tcp_server()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nShutting down..."
        )

        send_to_arduino(
            {
                "type":
                "stop"
            }
        )

        close_arduino()
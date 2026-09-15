

print("================================")
print(" Raspberry Pi Sensor Test")
print(" DHT22 + MQ5 + ADS1115")
print("================================")
print()


while True:

    # ----- DHT22 -----
    try:
        temperature = dht.temperature
        humidity = dht.humidity

    except RuntimeError:
        temperature = None
        humidity = None

    # ----- MQ5 -----
    mq5_voltage = mq5.voltage
    mq5_raw = mq5.value

    print("--------------------------------")

    if temperature is not None:
        print(f"Temperature : {temperature:.1f} °C")
        print(f"Humidity    : {humidity:.1f} %")
    else:
        print("DHT22       : Reading error")

    print(f"MQ5 Raw     : {mq5_raw}")
    print(f"MQ5 Voltage : {mq5_voltage:.3f} V")

    time.sleep(2)

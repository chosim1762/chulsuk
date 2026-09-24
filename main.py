# main.py
import bluetooth
import time
from ble_advertising import advertising_payload
from read_temp import read_cpu_temp

# Initialize BLE
ble = bluetooth.BLE()
ble.active(True)

# Define an event handler for connections (optional but helpful)
def ble_irq(event, data):
    if event == 1:  # _IRQ_CENTRAL_CONNECT
        print("Central device connected!")
    elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
        print("Central device disconnected. Restarting advertising...")
        advertise()

# Create the payload (Name limit is roughly 20 chars depending on flags)
# Note: Keep the name relatively short to avoid payload overflow errors

def advertise():
    # interval_us: 100,000 microseconds = 100 ms intervals
    temperature = read_cpu_temp()
    payload = advertising_payload(name="ENGR-BLE", services=[bluetooth.UUID(0x181A)])
    ble.gap_advertise(100000, adv_data=payload, connectable=True)

# Start advertising
print("Starting BLE Advertiser... Look for 'ESP32-BLE' on your phone.")
advertise()

# Register the interrupt handler
ble.irq(ble_irq)

# Keep the script running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping BLE...")
    ble.gap_advertise(None) # Passing None stops the advertising loop
    ble.active(False)

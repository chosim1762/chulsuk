# ble_advertising.py
import struct

# Advertising constants
_ADV_TYPE_FLAGS = 0x01
_ADV_TYPE_NAME = 0x09
_ADV_TYPE_UUID16_COMPLETE = 0x03
_ADV_TYPE_UUID32_COMPLETE = 0x05
_ADV_TYPE_UUID128_COMPLETE = 0x07

def advertising_payload(limited_disc=False, br_edr_not_supported=True, name=None, services=None):
    payload = bytearray()

    def append_data(adv_type, value):
        nonlocal payload
        payload.append(len(value) + 1)
        payload.append(adv_type)
        payload.extend(value)

    # Flags payload component
    flags = 0
    if limited_disc:
        flags |= 0x01 # LE Limited Discoverable Mode
    else:
        flags |= 0x02 # LE General Discoverable Mode
    if br_edr_not_supported:
        flags |= 0x04 # BR/EDR Not Supported
    append_data(_ADV_TYPE_FLAGS, struct.pack("B", flags))

    # Name payload component
    if name:
        append_data(_ADV_TYPE_NAME, name.encode("utf-8"))

    # Services UUIDs payload component
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                append_data(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                append_data(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                append_data(_ADV_TYPE_UUID128_COMPLETE, b)

    return payload

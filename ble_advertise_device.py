# main.py
import bluetooth
import struct
import time
import esp32

def read_cpu_temp():
    # ESP32 내부 CPU 온도 읽기 (섭씨 ℃)
    temp_celsius = esp32.mcu_temperature()
    return temp_celsius

# -------------------------------------------------------
# BLE advertising payload 생성 함수
# -------------------------------------------------------
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)

def advertising_payload(name=None, services=None):
    payload = bytearray()

    def append(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type) + value)

    # BLE 일반 검색 가능 + BR/EDR 미지원
    append(_ADV_TYPE_FLAGS, b"\x06")

    # 완전한 16-bit Service UUID 목록
    if services:
        uuid16_data = bytearray()
        for service in services:
            # 16-bit UUID 기준
            uuid16_data.extend(struct.pack("<H", service))
        append(_ADV_TYPE_UUID16_COMPLETE, uuid16_data)

    # 기기 이름
    if name:
        append(_ADV_TYPE_NAME, name.encode())

    return payload


# -------------------------------------------------------
# BLE 설정
# -------------------------------------------------------
DEVICE_NAME = "ENGR-LAB"
ADV_INTERVAL_US = 250_000  # 250 ms

# 표준 Device Information Service
_UUID_DIS = bluetooth.UUID(0x180A)

# 표준 DIS Characteristic UUID
_UUID_MANUFACTURER = bluetooth.UUID(0x2A29)
_UUID_MODEL_NUMBER = bluetooth.UUID(0x2A24)
_UUID_SERIAL_NUMBER = bluetooth.UUID(0x2A25)
_UUID_FIRMWARE_REV = bluetooth.UUID(0x2A26)

_UUID_BATTERY_SERVICE = bluetooth.UUID(0x180F)
_UUID_BATTERY_LEVEL = bluetooth.UUID(0x2A19)

_UUID_ESS = bluetooth.UUID(0x181A)
_UUID_TEMPERATURE = bluetooth.UUID(0x2A6E)

# 읽기 전용 특성
_READ = bluetooth.FLAG_READ

# GATT 서비스 정의
_DIS_SERVICE = (
    _UUID_DIS,
    (
        (_UUID_MANUFACTURER, _READ),
        (_UUID_MODEL_NUMBER, _READ),
        (_UUID_SERIAL_NUMBER, _READ),
        (_UUID_FIRMWARE_REV, _READ),
    ),
)

_BATTERY_LEVEL_CHAR = (
    _UUID_BATTERY_LEVEL,
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)

_BATTERY_SERVICE = (
    _UUID_BATTERY_SERVICE,
    (_BATTERY_LEVEL_CHAR,),
)

_CHAR_TEMPERATURE = (
    _UUID_TEMPERATURE,
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)

_ESS_SERVICE = (
    _UUID_ESS,
    (
        _CHAR_TEMPERATURE,
    ),
)

class DeviceInformationBLE:
    def __init__(self, initial_level=100):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        # GATT 서비스 등록 후 각 characteristic value handle 획득       
        handles = self.ble.gatts_register_services((_DIS_SERVICE,_BATTERY_SERVICE,_ESS_SERVICE,))
        
        self._manufacturer_handle = handles[0][0]
        self._model_handle = handles[0][1]
        self._serial_handle = handles[0][2]
        self._firmware_handle = handles[0][3]
        
        self.battery_handle = handles[1][0]
        self.set_battery_level(initial_level, notify=False)
        
        self.temperature_handle = handles[2][0]
        self.set_environment(temperature_c=10.00, notify=False)
        
        # Device Information 값 입력
        self.ble.gatts_write(self._manufacturer_handle, b"KU Engr")
        self.ble.gatts_write(self._model_handle, b"ESP32-BLE-01")
        self.ble.gatts_write(self._serial_handle, b"ESP32-000001")
        self.ble.gatts_write(self._firmware_handle, b"1.0.0")

        self._advertise()

    def _irq(self, event, data):
        # Central(스마트폰 등) 연결
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            conn_handle, addr_type, addr = data
            print("BLE connected:", conn_handle)

        # Central 연결 해제
        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            conn_handle, addr_type, addr = data
            print("BLE disconnected:", conn_handle)

            # 끊어지면 다시 광고 시작
            self._advertise()

    def _advertise(self):
        adv_data = advertising_payload(
            name=DEVICE_NAME,
            services=[0x180A, 0x180F, 0x181A],  # Device Information Service 0x180A
                                                # Battery 0x180F, Environmental Sensing 0x181A
        )
        self.ble.gap_advertise(ADV_INTERVAL_US, adv_data=adv_data)
        print("Advertising started:", DEVICE_NAME)
        
    def set_battery_level(self, level, notify=True):
        level = max(0, min(100, int(level)))
        value = struct.pack("B", level)
        self.ble.gatts_write(self.battery_handle, value)

        if notify:
            for conn_handle in self.connections:
                try:
                    self.ble.gatts_notify(conn_handle, self.battery_handle, value)
                except OSError:
                    pass
        print("Battery level: {}%".format(level))


    def set_temperature(self, temperature_c, notify=True):
        temperature_c = read_cpu_temp()
        value = struct.pack("<f", temperature_c)
        self.ble.gatts_write(self.temperature_handle, value)
        if notify:
            self._notify(self.temperature_handle, value)
            
    def set_environment(self, temperature_c, notify=True):
        self.set_temperature(temperature_c, notify)

# 실행
ble_device = DeviceInformationBLE()

while True:
    time.sleep(1)

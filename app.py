import serial
import pygame
from pygame import mixer
import os
import time
import glob

# Initialize pygame mixer
pygame.mixer.init()

# Configure the serial connection
port = '/dev/tty.usbmodem11101'
max_retries = 5
retry_delay = 2  # seconds

def connect_serial(port, max_retries, retry_delay):
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1} to connect to {port}")
            ser = serial.Serial(port, 9600, timeout=0.1)
            print(f"Successfully connected to {port}")
            return ser
        except serial.SerialException as e:
            print(f"Error connecting to {port}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Unable to connect.")
                return None

ser = connect_serial(port, max_retries, retry_delay)
if ser is None:
    exit(1)

# Load packs
def load_packs():
    packs = []
    pack_folders = sorted(glob.glob('packs/*'))
    default_index = pack_folders.index('packs/default') if 'packs/default' in pack_folders else 0
    pack_folders = pack_folders[default_index:] + pack_folders[:default_index]
    
    for folder in pack_folders:
        pack = {
            'B1': os.path.join(folder, 'amen.wav'),
            'T1': os.path.join(folder, 'morph.wav'),
            'T2': os.path.join(folder, 'vocal.wav')
        }
        packs.append(pack)
    return packs

packs = load_packs()
current_pack_index = 0

# Load sounds for the current pack
def load_sounds(pack):
    sounds = {}
    for key, file in pack.items():
        if os.path.exists(file):
            sounds[key] = pygame.mixer.Sound(file)
            print(f"Loaded {file}")
        else:
            print(f"Warning: {file} not found")
            sounds[key] = None
    return sounds

sounds = load_sounds(packs[current_pack_index])

# Keep track of which sounds are playing
sound_channels = {key: pygame.mixer.Channel(i) for i, key in enumerate(sounds)}
sound_states = {key: False for key in sounds}

# Knob state
knob_state = False

print("Listening for Arduino input...")

while True:
    try:
        if ser.in_waiting:
            message = ser.readline().decode('utf-8').strip()
            print(f"Received message: {message}")
            if ':' in message:
                input_key, state = message.split(':')
                if input_key == "KNOB":
                    knob_state = (state == "1")
                    print(f"Knob state: {'On' if knob_state else 'Off'}")
                elif input_key in sounds and sounds[input_key] is not None:
                    if state == '1' or (knob_state and sound_states[input_key]):
                        # Start or continue looping the sound
                        if not sound_channels[input_key].get_busy():
                            sound_channels[input_key].play(sounds[input_key], loops=-1)
                        sound_states[input_key] = True
                        print(f"Playing {input_key} (looping)")
                    elif state == '0' and not knob_state:
                        # Stop the sound
                        sound_channels[input_key].stop()
                        sound_states[input_key] = False
                        print(f"Stopped playing {input_key}")
                    
                    print(f"{input_key}: {'Playing' if sound_states[input_key] else 'Stopped'}")
            elif message == "PACK_SWITCH":
                current_pack_index = (current_pack_index + 1) % len(packs)
                sounds = load_sounds(packs[current_pack_index])
                print(f"Switched to pack: {os.path.basename(os.path.dirname(packs[current_pack_index]['B1']))}")
    except serial.SerialException as e:
        print(f"Serial connection lost: {e}")
        ser.close()
        ser = connect_serial(port, max_retries, retry_delay)
        if ser is None:
            break
    except KeyboardInterrupt:
        print("Program terminated by user")
        break
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Error details: {type(e).__name__}, {str(e)}")

# Clean up
if ser and ser.is_open:
    ser.close()
pygame.mixer.quit()
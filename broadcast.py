# Author: Çağrı Erdem, 2023
# Description: MIDI broadcasting script for 2groove web app.

import os
import queue
import threading

import clockblocks
import rtmidi

####################
## MIDI BROADCAST ##
####################

# Global control events
midi_obj = rtmidi.MidiFile("path_to_midi_file.mid")
generation_queue = queue.Queue(maxsize=4)
pause_event = threading.Event()
stop_event = threading.Event()
change_groove_event = threading.Event() # TODO: Event to change groove for the same tapped rhythm
current_bpm = 90
current_loop_count = 1 # How many times the current MIDI obj must be looped


# Constants
MS_PER_SEC = 1_000_000  # microseconds per second
BARS = 2
BEATS_PER_BAR = 4  # 4/4 time signature
BEAT_DURATION = 60 / current_bpm  # in seconds


def midi2events(midi_obj):
    '''(docstring)'''
    events = []
    tempo = None
    ticks_per_beat = midi_obj.ticks_per_beat
    for track in midi_obj.tracks:
        for msg in track:
            if msg.type == 'note_on' or msg.type == 'note_off':
                events.append((msg.time, msg.type, msg.note, msg.velocity))
            elif msg.type == 'set_tempo':
                tempo = msg.tempo
    return events, tempo, ticks_per_beat


def generate_midi_message(event_type, pitch, velocity):
    event_map = {'note_on': 0x90, 'note_off': 0x80}
    return [event_map.get(event_type, event_type), pitch, velocity]



def broadcasting_loop(generation_queue, stop_event, virtual_port=True, introduce_delay=False, verbose=False):
    '''This is a MIDI broadcasting loop implementation in terms of synchronization & time.
    It uses the clockblocks clock to synchronize the groove loops.'''
    
    global desired_loops, current_bpm

    # MIDI initialization
    midiout = rtmidi.MidiOut()
    available_ports = midiout.get_ports()
    print(f"Available MIDI ports: {available_ports}")
    if virtual_port:
        midiout.open_virtual_port("dB virtual output")
        print("Using dB virtual MIDI output")
    else:
        midiport = input("Enter the MIDI port")
        midiout.open_port(midiport)
        print(f"Using {midiport} as the MIDI port")
    current_midi_events = []
    print("Starting broadcasting loop...")

    def compute_groove_duration(current_tempo, ticks_per_beat, total_ticks):
        '''Computes the total duration of the groove in seconds.'''
        tempo_in_seconds_per_beat = current_tempo / MS_PER_SEC
        total_duration = tempo_in_seconds_per_beat * (total_ticks / ticks_per_beat)
        return total_duration    
        
    current_tempo = int(60_000_000 / current_bpm)  # Convert BPM to microseconds per beat
    current_loop_count = 0
    new_groove_queued = False  # This flag is set to True when a new groove enters the queue
    
    midi_obj = generation_queue.get()
    current_midi_events, current_tempo, ticks_per_beat = midi2events(midi_obj)
    tempo_in_seconds_per_tick = current_tempo / MS_PER_SEC / ticks_per_beat

    # Initialize master clock
    master_clock = clockblocks.Clock(timing_policy=0, initial_tempo=current_bpm).run_as_server() # 0 is equivalent to absolute timing, 1 is equivalent to relative timing.
    reference_start_time = master_clock.time()

    try:
        current_loop_count = 0  # Initialize loop count
        while not stop_event.is_set():
            total_ticks = sum(event[0] for event in current_midi_events)

            # If there's a new groove queued up, don't process it immediately. 
            # Just mark that a new groove is waiting. Wait for the current groove to loop for the desired number of times.
            if change_groove_event.is_set() and not generation_queue.empty():
                new_groove_queued = True
                change_groove_event.clear()  # Reset the event
                current_loop_count = 0  # Reset the loop count
                print(f"Detected a new groove queued – waiting for the current groove to loop {desired_loops} times")
            # First loop of the groove for the desired number of times, then switch to the new groove
            if new_groove_queued and current_loop_count >= desired_loops:
                midi_obj = generation_queue.get_nowait()
                current_midi_events, current_tempo, ticks_per_beat = midi2events(midi_obj)
                tempo_in_seconds_per_tick = current_tempo / MS_PER_SEC / ticks_per_beat
                print("Switched to the new groove")
                new_groove_queued = False  # Reset the flag
                current_loop_count = 0  # Reset the loop count
            
            master_clock.tempo = current_bpm  # Update the tempo
            if verbose:
                print(f"Master clock tempo: {master_clock.absolute_tempo()} BPM")
            groove_duration = compute_groove_duration(current_tempo, ticks_per_beat, total_ticks)
            # Compute the expected start time for this loop based on the reference
            expected_start_time = reference_start_time + (current_loop_count * groove_duration)

            # If we're ahead of the expected start time, wait
            while master_clock.time() < expected_start_time:
                master_clock.wait(0.01, units="time")  # Wait in small increments to be ready #TODO: Check the efficiency of this

            # Broadcast the current MIDI events.
            for event in current_midi_events:
                if stop_event.is_set():
                    break
                while pause_event.is_set():
                    master_clock.wait(0.1, units="time")

                timestamp, event_type, pitch, velocity = event
                message = generate_midi_message(event_type, pitch, velocity)
                midiout.send_message(message)

                master_clock.wait(timestamp * tempo_in_seconds_per_tick, units="time") # Locking the clock here
                # print(f"Master clock wait time: {timestamp * tempo_in_seconds_per_tick} seconds")

            current_loop_count += 1
            print(f"Current groove looped {current_loop_count} times")

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        del midiout





# Initialization of global events and queues
midi_app = Flask(__name__)# Connect to the browser interface
CORS(midi_app)

@midi_app.route('/set_params', methods=['POST'])
def receive_tapped_rhythms():
    global current_bpm, current_temp, current_loop_count, hitTolerance

    data = request.json
    current_bpm = data.get('bpm', 120)
    desired_loops = data.get('loops', 2)  # Default to 2 loop if not provided
    print(f"\nTempo: {current_bpm} BPM")
    print(f"Loop {desired_loops} times")


    generation_queue.put(midi_obj)
    change_groove_event.set()  # Trigger the broadcasting loop to switch to the new groove
    current_loop_count = 0  # Reset the loop count here
    return jsonify({"message": "Processing MIDI file..."})



@midi_app.route('/control', methods=['POST'])
def control():

    action = request.json.get('action', '')
    if action == 'pause':
        pause_event.set()
    elif action == 'resume':
        pause_event.clear()
        
    elif action == 'stop':
        os.kill(os.getpid(), signal.SIGINT)  # similar to cmd+C
        return jsonify({"message": f"Action {action} processed, server stopped"})

    return jsonify({"message": f"Action {action} processed"})


@midi_app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response


# RUN THE THREADS
broadcasting_thread = threading.Thread(target=broadcasting_loop, args=(generation_queue, stop_event))
broadcasting_thread.daemon = True
broadcasting_thread.start()

if __name__ == "__main__":
    midi_app.run(threaded=True, debug=True, port=5005)
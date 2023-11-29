# README for 2groove MIDI Broadcasting Script

## Overview
This script serves as a MIDI broadcasting tool for the 2groove web application. It allows for the playback and manipulation of MIDI files, integrating a Flask web server to handle control signals and parameters. 

## Features
- MIDI File Playback: Plays MIDI files and loops them as required.
- Dynamic Control: Receives control signals to pause, resume, and stop playback.
- Real-time Adjustments: Allows for real-time changes in tempo, loops, and groove.
- Web Interface: Flask app to receive and process parameters from a web interface.
- Virtual MIDI Ports: Supports the creation of virtual MIDI ports for broadcasting.

## Requirements
- Python 3.x
- Flask
- clockblocks
- rtmidi
- A MIDI file to play (`.mid` format)

## Installation
1. Install the required Python packages:
   ```bash
   pip install Flask clockblocks rtmidi

## Usage
1. Update the `path_to_midi_file.mid` in the script with the path to your MIDI file.
2. Run the script:
   ```bash
   python [script_name].py

## API Endpoints
- `/set_params` (POST): Set the BPM, loops, and initiate playback of a new MIDI file.
- `/control` (POST): Send control actions (pause, resume, stop).


Note: Ensure to adapt paths and configurations as per your environment and requirements.
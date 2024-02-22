# PyTinySoundFont

This project is a Python package that provides Python bindings for
[TinySoundFont](https://github.com/schellingb/TinySoundFont). This lets you
generate audio using SoundFont instruments (`.sf2`) in Python.

Python bindings are created using
[pybind11](https://github.com/pybind/pybind11).

## Installation

To install from source in this repository, clone this repository then do:

    pip install .

## Basic Usage

Each SF2 instrument is loaded into its own object:

    sf = tinysoundfont.SoundFont('test/example.sf2')

Setup the output format and global volume:

    sf.set_output(tinysoundfont.OutputMode.StereoInterleaved, 44100, -18.0)

The negative global gain lets multiple notes mix without distortion. The correct
value to use will depend on how many notes you expect to play and the gain
settings of the particular `sf2` instrument.

Play a note with:

    # Play preset 0, MIDI note 80, at full velocity
    sf.note_on(0, 80, 1.0)

Now create a buffer for the instrument to render to. This buffer can be anything
that follows the Python buffer protocol. For example, this can be objects of
type `bytearray`, `numpy.ndarray`, and many other things. The buffer can be 1D
or 2D. If it is 1D then it is expected to be a simple contiguous array of bytes
that will be filled with audio samples. If it is 2D then it is expected to have
correct format type `float32` and dimensions `(samples, channels)` where
`channels` will be 1 (mono) or 2 (stereo). Samples are always generated in
`float32` format.

    # Create an empty 1 second buffer for stereo float32 at 44.1 KHz
    buffer = bytearray(44100 * 4 * 2)

Generate samples using:

    sf.render(buffer)

The buffer now contains audio data for the playing instrument.

## Playing sound

To play actual sound you need something like
[`pyaudio`](https://pypi.org/project/PyAudio/). This package just generates
audio sample data for playback.

PyAudio can play back sound using "blocking mode" or "callback mode". This
package is compatible with both mechanisms.

### Blocking mode

Here is code showing simple setup of `pyaudio` and writing 1 second of audio
data with a note playing.

    import pyaudio
    import tinysoundfont

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=2,
                    rate=44100,
                    output=True)
    sf = tinysoundfont.SoundFont('test/example.sf2')
    sf.set_output(tinysoundfont.OutputMode.StereoInterleaved, 44100, -18.0)
    sf.channel_set_preset_index(0, 0)
    buffer = bytearray(44100 * 2 * 4)
    sf.channel_note_on(0, 48, 1.0)
    sf.render(buffer)
    # PyAudio requires immutable `bytes`, not mutable `bytearray`
    stream.write(bytes(buffer))
    stream.close()
    p.terminate()

Some details from the example above:

-   The format of the output stream opened must be `pyaudio.paFloat32` to match
    `float` format of rendered audio buffer.
-   The data written to `pyaudio` streams must be `bytes`, cannot be `bytearray`
    directly or `numpy.ndarray`.

### Callback mode

Here is code showing callback mode in `pyaudio`.

    import pyaudio
    import time
    sf = tinysoundfont.SoundFont('test/example.sf2')
    sf.set_output(tinysoundfont.OutputMode.StereoInterleaved, 44100, -18.0)
    p = pyaudio.PyAudio()

    def callback(in_data, frame_count, time_info, status):
        channels = 2
        bytes_per_sample = 4
        buffer = bytearray(frame_count * channels * bytes_per_sample)
        sf.render(buffer)
        return (bytes(buffer), pyaudio.paContinue)

    stream = p.open(format=pyaudio.paFloat32,
                    channels=2,
                    rate=44100,
                    output=True,
                    stream_callback=callback)

    time.sleep(0.5)
    sf.channel_set_preset_index(0, 0)
    sf.channel_note_on(0, 48, 1.0)
    time.sleep(1)
    stream.close()
    p.terminate()

Some details from the example above:

-   The callback function is provided `frame_count` which is used to create a
    buffer and fill it with rendered sound.
-   Returning `pyaudio.paContinue` as the second part of the tuple in the return
    value keeps the callback active and being called.
-   During the `time.sleep(1)` call, the callback is being called many times and
    continues rendering in a separate thread.

### Audio organization

In general, interactive applications need to use the callback mode of `pyaudio`.
Using blocking mode means that no interaction is possible during audio playback.

For applications that want to synchronize video rendering and audio playback
there are a few choices. One choice is to handle audio callbacks as fast as
possible with smallest buffer possible. This is the `pyaudio` default
configuration if no `frames_per_buffer` is passed to `pyaudio.open`. In the
callback, output audio based on what is happening right then. This method will
have the lowest latency. Because of the arbitrary nature of buffer sizes this
method can introduce jitter to event timings.

Another option is to request a buffer size that matches the "rhythm" of the
game. For example a buffer of 441 samples at 44.1 kHz will be refilled exactly
100 times a second. If the game action happens at 120 BPM, that means each beat
will span exactly 50 callback buffer fills. The idea here is to keep track of
the number of audio callbacks as a master clock for actions and synchronization.
Video frames can then be synchronized to the latest audio count taking into
account any fixed playback or video synchronization delays. This method
has higher latency but lower jitter and consistent delay.

A final option is to use the smallest buffer possible to minimize latency but
also record timing information for every event. Then during audio rendering use
the timing information to position the events to the correct sample. For
example, a single `noteon` event might need to happen half way through a buffer
in the callback. This could be accomplished with the following code:

    # Assume we are inside a PyAudio callback
    buffer = memoryview(bytearray(frame_count * 2 * 4))
    start = frame_count * 2 * 4 // 2
    # Render first half
    sf.render(buffer[:start])
    sf.channel_note_on(0, 48, 1.0)
    # Render second half
    sf.render(buffer[start:])
    return (bytes(buffer), pyaudio.paContinue)

It is important to wrap the `bytearray` buffer with `memoryview` so that the
slicing operations into the buffer do not copy memory in the buffer but instead
refer to subsections of the buffer.

## Local build and test

Build and install locally with:

    pip install .

Test in the root directory with:

    pytest

You may want to build and test in a `virtualenv` environment.

The `pip install .` will perform a compilation step for `C++` code. Your
environment must have access to a working `C++` compiler as well as the Python
development headers.

## Compressed SoundFonts

This package also supports a compressed SoundFont2 format `.sfo` by using
[std_vorbis.c](https://github.com/nothings/stb/blob/master/stb_vorbis.c). The
compressed `.sfo` format is similar to regular `.sf2` but the audio waveforms
are stored with Ogg/Vorbis compression instead of being stored uncompressed.
This is especially useful for large General MIDI soundbanks that contain many
instruments in one file. For information about converting SoundFonts see
[SFOTool](https://github.com/schellingb/TinySoundFont/tree/master/sfotool).

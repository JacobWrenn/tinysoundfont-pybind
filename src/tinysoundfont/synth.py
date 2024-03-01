from . import _tinysoundfont

# Drum channels have separate samples per key
DRUM_CHANNEL = 10


class SoundFontException(Exception):
    pass


class Synth:
    """Synth represents a synthesizer that can load a SoundFont and produce audio"""

    def _get_soundfont(self, sfid):
        if sfid not in self.soundfonts:
            raise SoundFontException("Invalid SoundFont id")
        return self.soundfonts[sfid]

    def _get_sfid(self, chan):
        if chan not in self.channel:
            raise SoundFontException("Invalid channel (channel not assigned)")
        return self.channel[chan]

    def __init__(self, gain=0, samplerate=44100):
        """Create new synthesizer object to control sound generation

        Keyword arguments:
        gain -- scale factor for audio output in relative dB (default 0.0)
        samplerate : output samplerate in Hz (default 44100)

        If you need to mix many simultaneous voices you may need to turn down
        the gain to avoid clipping. Some SoundFonts also require gain adjustment
        to avoid being too loud or too quiet.
        """
        self.p = None
        self.stream = None
        self.gain = gain
        self.samplerate = samplerate
        # soundfonts maps sfid numbers to SoundFont objects
        self.soundfonts = {}
        # Unique identifier creator for this Synth
        self.next_sfid = 0
        # Keep track of which SoundFont to use for different channels
        # Dictionary of channel -> sfid
        self.channel = {}

    def sfload(self, filename, gain=0.0, max_voices=256):
        """Load SoundFont and return its ID

        Arguments:
        filename -- filename containing sf2/sf3/sfo SoundFont data, or `bytes` data directly

        Keyword arguments:
        gain -- gain adjustment for this SoundFont in relative dB (default 0.0)
        max_voices -- maximum number of simultaneous voices (default 256)

        Returns ID of SoundFont to be used by other methods such as `program_select`.
        One note in a SoundFont may use more than one voice. Playing multiple notes
        also uses more voices. If more voices are required than are available, older
        voices will be cut off.
        """
        soundfont = _tinysoundfont.SoundFont(filename)
        soundfont.set_output(
            _tinysoundfont.OutputMode.StereoInterleaved,
            self.samplerate,
            self.gain + gain,
        )
        soundfont.set_max_voices(max_voices)
        sfid = self.next_sfid
        self.next_sfid += 1
        self.soundfonts[sfid] = soundfont
        return sfid

    def sfunload(self, sfid):
        """Unload a SoundFont and free memory it used"""
        _ = self._get_soundfont(sfid)
        del self.soundfonts[sfid]
        # Clear any channels that refers to this sfid
        self.channel = {
            chan: self.channel[chan]
            for chan in self.channel
            if self.channel[chan] != sfid
        }

    def program_select(self, chan, sfid, bank, preset):
        """Select a program for specific channel"""
        soundfont = self._get_soundfont(sfid)
        self.channel[chan] = sfid
        soundfont.channel_set_bank(chan, bank)
        soundfont.channel_set_preset_number(chan, preset, chan == DRUM_CHANNEL)

    def program_unset(self, chan):
        """Set the preset of a MIDI channel to an unassigned state"""
        if chan not in self.channel:
            raise SoundFontException("Invalid channel (channel not assigned)")
        del self.channel[chan]

    def program_info(self, chan):
        """Get SoundFont id, bank, program number, and preset name of channel"""
        sfid = self._get_sfid(chan)
        soundfont = self._get_soundfont(sfid)
        bank = soundfont.channel_get_preset_bank(chan)
        preset = soundfont.channel_get_preset_number(chan)
        return (sfid, bank, preset)

    def sfpreset_name(self, sfid, bank, number):
        """Return name of a SoundFont preset"""
        soundfont = self._get_soundfont(sfid)
        return soundfont.get_preset_name(bank, number)

    def noteon(self, chan, key, vel):
        """Play a note"""
        if key < 0 or key > 127:
            return False
        if vel < 0 or vel > 127:
            return False
        if chan not in self.channel:
            return False
        sfid = self._get_sfid(chan)
        soundfont = self._get_soundfont(sfid)
        soundfont.channel_note_on(chan, key, vel / 127.0)
        return True

    def noteoff(self, chan, key):
        """Stop a note"""
        if key < 0 or key > 127:
            return False
        if chan not in self.channel:
            return False
        sfid = self._get_sfid(chan)
        soundfont = self._get_soundfont(sfid)
        soundfont.channel_note_off(chan, key)
        return True

    def start(self, driver=None):
        """Start audio playback"""
        # Import pyaudio here so if this function is not used there is no dependency
        import pyaudio

        def callback(in_data, frame_count, time_info, status):
            CHANNELS = 2
            SIZEOF_FLOAT_IN_BYTES = 4
            buffer = bytearray(frame_count * CHANNELS * SIZEOF_FLOAT_IN_BYTES)
            mix = False
            for soundfont in self.soundfonts.values():
                soundfont.render(buffer, mix)
                # After first render turn on mix to mix together all sounds
                mix = True
            return (bytes(buffer), pyaudio.paContinue)

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=2,
            rate=self.samplerate,
            output=True,
            stream_callback=callback,
        )

    def stop(self):
        """Stop audio playback"""
        if self.p is not None and self.stream is not None:
            self.stream.close()
            self.p.terminate()

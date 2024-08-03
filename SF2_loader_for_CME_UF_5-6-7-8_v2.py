import fluidsynth
import rtmidi
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

class DAWApp:
    def __init__(self):
        # Initialize FluidSynth
        self.fs = fluidsynth.Synth()
        self.fs.start(driver='pipewire')  # Set audio output to pipewire
        self.sfid = None  # Store the loaded soundfont ID

        # Initialize Gtk window and user interface
        self.window = Gtk.Window(title="SF2_loader_for_CME_UF_5-6-7-8")
        self.window.connect("destroy", Gtk.main_quit)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.window.add(self.vbox)
        self.vbox.set_center_widget(Gtk.Alignment.new(0.5, 0.5, 1, 1))

        # Add a display area for current information
        self.info_view = Gtk.TextView()
        self.info_view.set_size_request(350, 100)  # Size 350x100px
        self.info_view.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("orange"))  # Orange background
        self.info_view.modify_font(Pango.FontDescription("Sans Bold 20"))  # Font Sans Bold 20
        self.info_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.info_buffer = self.info_view.get_buffer()
        self.lcd_tag = self.info_buffer.create_tag("lcd_style", scale=0.833, weight=Pango.Weight.BOLD)
        self.vbox.pack_start(self.info_view, False, False, 0)

        # List SF2 files in the application directory
        sf2_directory = "./sf2"
        self.sf2_files = [file for file in os.listdir(sf2_directory) if file.endswith(".sf2")]

        # SF2 file selection
        self.sf2_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.sf2_label = Gtk.Label(label="SF2:")
        self.sf2_combo = Gtk.ComboBoxText()
        for sf2_file in self.sf2_files:
            self.sf2_combo.append_text(sf2_file)
        self.sf2_combo.connect("changed", self.on_sf2_changed)
        self.sf2_prev_button = Gtk.Button(label="<")
        self.sf2_next_button = Gtk.Button(label=">")
        self.sf2_prev_button.connect("clicked", self.on_sf2_prev_clicked)
        self.sf2_next_button.connect("clicked", self.on_sf2_next_clicked)
        self.sf2_box.pack_start(self.sf2_label, False, False, 0)
        self.sf2_box.pack_start(self.sf2_combo, False, False, 0)
        self.sf2_box.pack_start(self.sf2_prev_button, False, False, 0)
        self.sf2_box.pack_start(self.sf2_next_button, False, False, 0)
        self.vbox.pack_start(self.sf2_box, False, False, 0)

        # Preset selection
        self.preset_label = Gtk.Label(label="Preset:")
        self.preset_combo = Gtk.ComboBoxText()
        self.preset_combo.set_active(0)  # Set to 0 by default
        self.preset_combo.connect("changed", self.on_preset_changed)
        self.vbox.pack_start(self.preset_label, False, False, 0)
        self.vbox.pack_start(self.preset_combo, False, False, 0)

        # MIDI input selection
        self.midi_label = Gtk.Label(label="MIDI Input:")
        self.midi_combo = Gtk.ComboBoxText()
        self.midi_in_ports = self.get_midi_in_ports()
        for port in self.midi_in_ports:
            self.midi_combo.append_text(port)
        self.midi_combo.connect("changed", self.on_midi_changed)
        self.vbox.pack_start(self.midi_label, False, False, 0)
        self.vbox.pack_start(self.midi_combo, False, False, 0)

        self.midi_in = None

        # Start the main program loop
        self.window.show_all()
        Gtk.main()

    def get_midi_in_ports(self):
        midi_in = rtmidi.RtMidiIn()
        ports = []
        for i in range(midi_in.getPortCount()):
            ports.append(midi_in.getPortName(i))
        return ports

    def on_sf2_changed(self, combo):
        sf2_file = combo.get_active_text()
        if sf2_file:
            self.load_all_presets(os.path.join("./sf2", sf2_file))
            self.update_info_view()

    def on_sf2_prev_clicked(self, button):
        index = self.sf2_combo.get_active()
        if index > 0:
            self.sf2_combo.set_active(index - 1)

    def on_sf2_next_clicked(self, button):
        index = self.sf2_combo.get_active()
        if index < len(self.sf2_files) - 1:
            self.sf2_combo.set_active(index + 1)

    def on_preset_changed(self, combo):
        sf2_file = self.sf2_combo.get_active_text()
        if sf2_file:
            preset_text = self.preset_combo.get_active_text()
            index = int(preset_text.split(":")[0])
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), index)
            self.update_info_view()

    def on_midi_changed(self, combo):
        midi_port = combo.get_active_text()
        if midi_port:
            if self.midi_in is not None:
                self.midi_in.closePort()
            self.midi_in = rtmidi.RtMidiIn()
            self.midi_in.openPort(self.midi_in_ports.index(midi_port))
            self.midi_in.setCallback(self.handle_midi_event)

    def load_all_presets(self, filename):
        # Unload previous soundfont if any
        if self.sfid is not None:
            self.fs.sfunload(self.sfid)

        # Load the SF2 file
        self.sfid = self.fs.sfload(filename)
        self.fs.program_reset()

        # Remove all items from the preset combo box
        self.preset_combo.remove_all()

        # Get preset names and load them
        preset_names = self.get_preset_names()
        for i, (bank, preset, name) in enumerate(preset_names):
            self.preset_combo.append_text(f"{i}: {name} (Bank {bank}, Preset {preset})")
            try:
                self.fs.program_select(0, self.sfid, bank, preset)
            except:
                print(f"Could not load preset {i}: {name}")

        if self.preset_combo.get_model().iter_n_children(None) > 0:
            self.preset_combo.set_active(0)

    def get_preset_names(self):
        preset_names = []
        for bank in range(129):  # GM spec defines 128 banks, but we'll check 0-128 to be safe
            for preset in range(128):
                name = self.fs.sfpreset_name(self.sfid, bank, preset)
                if name:
                    preset_names.append((bank, preset, name))
        return preset_names

    def load_sf2_instrument(self, filename, index):
        if self.sfid is None or filename != self.fs.get_sfont_name(self.sfid):
            if self.sfid is not None:
                self.fs.sfunload(self.sfid)
            self.sfid = self.fs.sfload(filename)

        preset_names = self.get_preset_names()
        if 0 <= index < len(preset_names):
            bank, preset, name = preset_names[index]
            channel = 0  # Always use the first channel for simplicity
            try:
                self.fs.program_select(channel, self.sfid, bank, preset)
            except:
                print(f"Could not load preset {index}: {name}")

    def handle_midi_event(self, message, data=None):
        if message[0] == 0xC0:  # Program change message
            channel = message[0] & 0x0F
            preset = message[1]
            if preset < self.preset_combo.get_model().iter_n_children(None):
                self.preset_combo.set_active(preset)  # Set the active preset in the combo box
            else:
                print(f"Preset {preset} is not available in this SF2 file")

    def update_info_view(self):
        sf2_file = self.sf2_combo.get_active_text()
        preset = self.preset_combo.get_active_text()

        info_text = f"SF2: {sf2_file}\nPreset: {preset}"
        self.info_buffer.set_text(info_text)

        # Apply the LCD style to the text in the display
        start_iter = self.info_buffer.get_start_iter()
        end_iter = self.info_buffer.get_end_iter()
        self.info_buffer.apply_tag_by_name("lcd_style", start_iter, end_iter)

    def cleanup(self):
        # Close the program and cleanup
        if self.sfid is not None:
            self.fs.sfunload(self.sfid)
        self.fs.delete()

if __name__ == "__main__":
    app = DAWApp()
    app.cleanup()

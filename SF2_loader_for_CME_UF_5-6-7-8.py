import re
import fluidsynth
import rtmidi
import os
import subprocess

from gi.repository import Gtk

class DAWApp:
    def __init__(self):
        # Inicjalizacja FluidSynth
        self.fs = fluidsynth.Synth()
        self.fs.start(driver='jack')

        # Inicjalizacja okna Gtk i interfejsu użytkownika
        self.window = Gtk.Window(title="SF2_loader_for_CME_UF_5-6-7-8")
        self.window.connect("destroy", Gtk.main_quit)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.window.add(self.vbox)

        # Lista plików SF2 w katalogu aplikacji
        sf2_directory = "./sf2"
        self.sf2_files = [file for file in os.listdir(sf2_directory) if file.endswith(".sf2")]

        # Lista rozwijalna z plikami SF2
        self.sf2_combo = Gtk.ComboBoxText()
        for sf2_file in self.sf2_files:
            self.sf2_combo.append_text(sf2_file)
        self.sf2_combo.connect("changed", self.on_sf2_changed)
        self.vbox.pack_start(self.sf2_combo, False, False, 0)

        # Przyciski do przełączania między plikami SF2
        self.prev_button = Gtk.Button(label="<")
        self.next_button = Gtk.Button(label=">")
        self.prev_button.connect("clicked", self.on_prev_button_clicked)
        self.next_button.connect("clicked", self.on_next_button_clicked)
        self.vbox.pack_start(self.prev_button, False, False, 0)
        self.vbox.pack_start(self.next_button, False, False, 0)

        # Lista rozwijalna z wyborem banku
        self.bank_label = Gtk.Label(label="Bank:")
        self.bank_combo = Gtk.ComboBoxText()
        for i in range(128):
            self.bank_combo.append_text(str(i))
        self.bank_combo.connect("changed", self.on_bank_preset_changed)
        self.vbox.pack_start(self.bank_label, False, False, 0)
        self.vbox.pack_start(self.bank_combo, False, False, 0)

        # Lista rozwijalna z wyborem presetu
        self.preset_label = Gtk.Label(label="Preset:")
        self.preset_combo = Gtk.ComboBoxText()
        self.preset_combo.connect("changed", self.on_preset_changed)
        self.vbox.pack_start(self.preset_label, False, False, 0)
        self.vbox.pack_start(self.preset_combo, False, False, 0)

        # Rozpoczęcie nasłuchiwania zdarzeń MIDI z klawiatury MIDI USB
        self.midi_in = rtmidi.MidiIn()
        self.midi_in.open_port(0)  # Wybierz odpowiedni port MIDI USB
        self.midi_in.set_callback(self.handle_midi_event)

        # Rozpoczęcie głównej pętli programu
        self.window.show_all()
        Gtk.main()

    def on_sf2_changed(self, combo):
        sf2_file = combo.get_active_text()
        if sf2_file:
            bank = int(self.bank_combo.get_active_text())
            preset = int(self.preset_combo.get_active_text())
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), bank, preset)

    def on_prev_button_clicked(self, button):
        index = self.sf2_combo.get_active()
        if index > 0:
            self.sf2_combo.set_active(index - 1)

    def on_next_button_clicked(self, button):
        index = self.sf2_combo.get_active()
        if index < len(self.sf2_files) - 1:
            self.sf2_combo.set_active(index + 1)

    def on_bank_preset_changed(self, combo):
        sf2_file = self.sf2_combo.get_active_text()
        if sf2_file:
            bank = int(self.bank_combo.get_active_text())
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), bank, preset=0)  # preset=0, aby zresetować preset do pierwszego

            # Usuń wszystkie elementy z listy rozwijalnej presetów
            self.preset_combo.remove_all()
            # Uzupełnij listę rozwijalną presetów z nazwami
            preset_names = self.get_preset_names(sf2_file)
            for name in preset_names:
                self.preset_combo.append_text(name)
            self.preset_combo.set_active(0)

    def on_preset_changed(self, combo):
        sf2_file = self.sf2_combo.get_active_text()
        if sf2_file:
            bank = int(self.bank_combo.get_active_text())
            preset = self.preset_combo.get_active()  # pobierz indeks aktywnego elementu z listy rozwijalnej
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), bank, preset)

    def get_preset_names(self, sf2_file):
        # Uruchomienie sf2parse w celu analizy pliku SF2
        output = subprocess.check_output(["bin/sf2parse", os.path.join("./sf2", sf2_file)]).decode("utf-8")
        
        # Wyodrębnienie nazw presetów z wyjścia sf2parse
        preset_pattern = re.compile(r'Preset\[\d+:\d+\] (\w+(?:\s+bag\w+)*)')
        preset_names = preset_pattern.findall(output)
        
        return preset_names

    def load_sf2_instrument(self, filename, bank, preset):
        sfid = self.fs.sfload(filename)
        channel = 0  # Dla uproszczenia używamy zawsze pierwszego kanału
        self.fs.program_select(channel, sfid, bank, preset)  # Ustawia wybrany bank i preset

    def handle_midi_event(self, message, data=None):
        if message[0] == 0xC0:  # Program change message
            channel = message[0] & 0x0F
            preset = message[1]
            self.preset_combo.set_active(preset)  # ustawienie aktywnego presetu na liście
            bank = int(self.bank_combo.get_active_text())
            self.load_sf2_instrument(os.path.join("./sf2", self.sf2_combo.get_active_text()), bank, preset)  # zmiana presetu w programie FluidSynth

    def cleanup(self):
        # Zamknięcie programu i zakończenie działania
        self.fs.delete()

if __name__ == "__main__":
    app = DAWApp()
    app.cleanup()

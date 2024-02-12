import re
import fluidsynth
import rtmidi
import os
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

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
        self.vbox.set_center_widget(Gtk.Alignment.new(0.5, 0.5, 1, 1))

        # Dodanie obszaru wyświetlającego aktualne informacje
        self.info_view = Gtk.TextView()
        self.info_view.set_size_request(350, 100)  # Rozmiar 700x100px
        self.info_view.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("orange"))  # Tło pomarańczowe
        self.info_view.modify_font(Pango.FontDescription("Sans Bold 20"))  # Czcionka Sans Bold 20
        self.info_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.info_buffer = self.info_view.get_buffer()
        self.lcd_tag = self.info_buffer.create_tag("lcd_style", scale=0.833, weight=Pango.Weight.BOLD)
        self.vbox.pack_start(self.info_view, False, False, 0)

        # Lista plików SF2 w katalogu aplikacji
        sf2_directory = "./sf2"
        self.sf2_files = [file for file in os.listdir(sf2_directory) if file.endswith(".sf2")]

        # Wybór pliku SF2
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

        # Wybór banku
        self.bank_label = Gtk.Label(label="Bank:")
        self.bank_combo = Gtk.ComboBoxText()
        for i in range(128):
            self.bank_combo.append_text(str(i))
        self.bank_combo.set_active(0)  # Domyślnie ustawiany na 0
        self.bank_combo.connect("changed", self.on_bank_preset_changed)
        self.vbox.pack_start(self.bank_label, False, False, 0)
        self.vbox.pack_start(self.bank_combo, False, False, 0)

        # Wybór presetu
        self.preset_label = Gtk.Label(label="Preset:")
        self.preset_combo = Gtk.ComboBoxText()
        self.preset_combo.set_active(0)  # Domyślnie ustawiany na 0
        self.preset_combo.connect("changed", self.on_preset_changed)
        self.vbox.pack_start(self.preset_label, False, False, 0)
        self.vbox.pack_start(self.preset_combo, False, False, 0)

        # Rozpoczęcie nasłuchiwania zdarzeń MIDI z klawiatury MIDI USB
        self.midi_in = rtmidi.RtMidiIn()
        self.midi_in.openPort(0)  # Wybierz odpowiedni port MIDI USB
        self.midi_in.setCallback(self.handle_midi_event)

        # Rozpoczęcie głównej pętli programu
        self.window.show_all()
        Gtk.main()

    def on_sf2_changed(self, combo):
        sf2_file = combo.get_active_text()
        if sf2_file:
            bank = int(self.bank_combo.get_active_text())
            preset = int(self.preset_combo.get_active_text())
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), bank, preset)
            self.update_info_view()

    def on_sf2_prev_clicked(self, button):
        index = self.sf2_combo.get_active()
        if index > 0:
            self.sf2_combo.set_active(index - 1)

    def on_sf2_next_clicked(self, button):
        index = self.sf2_combo.get_active()
        if index < len(self.sf2_files) - 1:
            self.sf2_combo.set_active(index + 1)

    def on_bank_preset_changed(self, combo):
        sf2_file = self.sf2_combo.get_active_text()
        if sf2_file:
            bank = int(self.bank_combo.get_active_text())
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), bank, preset=0)  
            self.update_info_view()

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
            preset = self.preset_combo.get_active()
            self.load_sf2_instrument(os.path.join("./sf2", sf2_file), bank, preset)
            self.update_info_view()

    def get_preset_names(self, sf2_file):
        # Uruchomienie sf2parse w celu analizy pliku SF2
        output = subprocess.check_output(["sf2parse", os.path.join("./sf2", sf2_file)]).decode("utf-8")
        
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

    def update_info_view(self):
        sf2_file = self.sf2_combo.get_active_text()
        bank = self.bank_combo.get_active_text()
        preset = self.preset_combo.get_active_text()

        info_text = f"SF2: {sf2_file}\nBank: {bank}\nPreset: {preset}"
        self.info_buffer.set_text(info_text)

        # Ustawienie stylu dla tekstu na wyświetlaczu LCD
        start_iter = self.info_buffer.get_start_iter()
        end_iter = self.info_buffer.get_end_iter()
        self.info_buffer.apply_tag_by_name("lcd_style", start_iter, end_iter)

    def cleanup(self):
        # Zamknięcie programu i zakończenie działania
        self.fs.delete()

if __name__ == "__main__":
    app = DAWApp()
    app.cleanup()

#!/bin/bash

# Funkcja do aktualizacji pliku XML
update_xml() {
    local old_name="$1"
    local new_name="$2"
    local xml_file="$3"

    sed -i "s/$old_name/$new_name/g" "$xml_file"
}

# Znajdź aktualną nazwę instancji FluidSynth używając pw-jack
current_fluidsynth=$(pw-jack jack_lsp | grep 'Midi-Bridge:FLUID Synth' | head -n 1 | sed 's/.*Midi-Bridge:\(FLUID Synth ([0-9]*)\).*/\1/')

if [ -z "$current_fluidsynth" ]; then
    echo "Nie znaleziono aktywnej instancji FluidSynth"
    exit 1
fi

echo "Aktualna instancja FluidSynth: $current_fluidsynth"

# Ścieżka do pliku XML
xml_file="connection.xml"

# Znajdź starą nazwę FluidSynth w pliku XML
old_fluidsynth=$(grep -oP '(?<=client name=")FLUID Synth \([0-9]+\)' "$xml_file" | head -n 1)

if [ -z "$old_fluidsynth" ]; then
    echo "Nie znaleziono starej nazwy FluidSynth w pliku XML"
    exit 1
fi

echo "Stara nazwa FluidSynth w XML: $old_fluidsynth"

# Aktualizuj plik XML
update_xml "$old_fluidsynth" "$current_fluidsynth" "$xml_file"

echo "Zaktualizowano plik XML"

# Wywołaj aj-snapshot z zaktualizowanym plikiem
pw-jack aj-snapshot -r "$xml_file"

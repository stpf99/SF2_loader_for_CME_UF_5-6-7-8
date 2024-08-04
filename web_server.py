from flask import Flask, render_template, jsonify, request
from SF2_loader import DAWApp
import threading

app = Flask(__name__)
daw_app = DAWApp(headless=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sf2_files')
def get_sf2_files():
    return jsonify(daw_app.sf2_files)

@app.route('/presets')
def get_presets():
    sf2_file = request.args.get('sf2_file')
    bank = int(request.args.get('bank', 0))
    presets = daw_app.get_preset_names(sf2_file)
    return jsonify([preset for preset in presets if int(preset[0].split(':')[0]) == bank])

@app.route('/load_instrument', methods=['POST'])
def load_instrument():
    data = request.json
    sf2_file = data['sf2_file']
    bank = int(data['bank'])
    preset = int(data['preset'])
    daw_app.load_sf2_instrument(f"./sf2/{sf2_file}", bank, preset)
    return jsonify({"status": "success"})

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    daw_app.run()

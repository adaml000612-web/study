"""Extend the existing native Proteus circuit without replacing its original file."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import struct

BASE = Path(r'D:\Documents\ChatGPT\study\实验4\输出\2026-10-12\Proteus_Ultrasonic_LCD1602')
API = BASE / 'tools/proteus-api/api'
INSTALL = Path(r'D:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional')
FIRMWARE = Path(r'D:\Desktop\Ultrasonic_Proximity_2026-10-13')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(API))
import component_codec as cc
import device_library as dl
cc.SOURCE = INSTALL / 'DATA/SAMPLES/Graph Based Simulation/Rescap.pdsprj'
OriginalLibrary = dl.Library
class InstalledLibrary(OriginalLibrary):
    def __init__(self, directory=INSTALL / 'DATA/LIBRARY'):
        super().__init__(directory)
dl.Library = InstalledLibrary

def mm(v):
    return round(v * 100000)

def run():
    original = BASE / 'Experiment4_Ultrasonic_LCD1602.pdsprj'
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    # Native editing has left a diagonal wire and zero-length terminal stubs
    # that this codec cannot preserve. Rebuild routes from the decoded semantic
    # endpoints while retaining every original component and its coordinates.
    from net_objects import decode_net_objects
    circuit = cc.Circuit(original)
    graph = decode_net_objects(circuit._project)
    assert graph['complete'] and graph['rebuild_complete']
    for ref, item in circuit._project._components.items():
        template = cc.template_from_component(circuit._project, ref)
        x, y = struct.unpack_from('<ii', circuit._project._dsn, item['xy_offset'])
        circuit._parts.append(dict(ref=ref, device=template['device'],
                                   value=item['fields'][1]['text'], x=x, y=y,
                                   template=template, properties={}))
    for edge in graph['connections']:
        circuit.connect(edge['first'], edge['second'])
    for terminal in graph['semantic_terminals']:
        assert terminal.get('pin') is not None
        circuit.add_terminal(terminal['kind'], terminal['name'], terminal['pin'])
    original_refs = {p['ref'] for p in circuit.components()}
    for device, library in [('2N3906', 'BIPOLAR'), ('SPEAKER', 'ACTIVE')]:
        circuit.import_device(device, library=library)
    # A PNP high-side driver matches the firmware's active-low enable polarity.
    # SPEAKER is the installed analogue audio transducer; it is a simulation
    # substitute for the physical passive buzzer, not its measured exact model.
    parts = [
        ('2N3906', 'Q1', '2N3906', 70, 20, {}),
        ('RESISTOR', 'R2', '1k', 45, 20, {}),
        ('RESISTOR', 'R4', '10k', 70, 40, {}),
        ('SPEAKER', 'LS1', 'BUZZER_SIM', 95, 0,
         {'LOAD': '100', 'VNOM': '5V'}),
        ('BUTTON', 'SW2', 'K3_PLUS', 35, 65, {}),
        ('BUTTON', 'SW3', 'K4_MINUS', 80, 65, {}),
        ('RESISTOR', 'R5', '10k', 35, 80, {}),
        ('RESISTOR', 'R6', '10k', 80, 80, {}),
        ('RESISTOR', 'R7', '100k', 115, 0, {}),
        ('RESISTOR', 'R8', '10k', -20, 45, {}),
    ]
    for device, ref, value, x, y, props in parts:
        circuit.add(device, ref, value, mm(x), mm(y), properties=props)
        circuit.update(ref, label_offsets={'reference': (mm(3), mm(3)),
                                          'value': (mm(3), mm(-1))})
    def terminal(kind, name, pin):
        circuit.add_terminal(kind, name, tuple(pin.split('.', 1)))
    def net(name, *pins):
        for pin in pins:
            terminal('label', name, pin)
    def power(pin):
        terminal('power', 'VCC', pin)
    def ground(pin):
        terminal('ground', 'GND', pin)
    net('BEEP', 'U1.P1.5', 'R2.1')
    net('BASE', 'R2.2', 'Q1.B', 'R4.1')
    power('Q1.E')
    power('R4.2')
    net('BUZZ', 'Q1.C', 'LS1.1', 'R7.1')
    ground('LS1.2')
    ground('R7.2')
    net('K3', 'U1.P3.2/$INT0$', 'SW2.1', 'R5.1')
    net('K4', 'U1.P3.3/$INT1$', 'SW3.1', 'R6.1')
    for pin in ['SW2.2', 'SW3.2']:
        ground(pin)
    for pin in ['R5.2', 'R6.2']:
        power(pin)
    net('ECHO', 'R8.1')
    ground('R8.2')
    circuit.update('US1', properties={'SETPOINT': '20'})
    hex_source = FIRMWARE / 'Objects/Ultrasonic_Proximity.hex'
    shutil.copyfile(hex_source, OUT / 'Ultrasonic_Proximity.hex')
    shutil.copyfile(FIRMWARE / 'main.c', OUT / 'main.c')
    circuit.update('U1', properties={'PROGRAM': 'Ultrasonic_Proximity.hex',
                                     'CLOCK': '11.0592MHz'})
    path = circuit.save(OUT / 'Ultrasonic_Proximity_Buzzer.pdsprj',
                        title='Ultrasonic Proximity - Passive Buzzer and Keys', overwrite=True)
    reopened = cc.Circuit.open(path)
    assert original_refs <= {p['ref'] for p in reopened.components()}
    assert len(reopened.components()) == len(original_refs) + len(parts)
    u1 = next(p for p in reopened.components() if p['ref'] == 'U1')
    assert u1['properties']['PROGRAM'] == 'Ultrasonic_Proximity.hex'
    assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
    result = {'project': path.name, 'components': len(reopened.components()),
              'original_unchanged': True, 'native_codec_reopen': True,
              'firmware_sha256': hashlib.sha256(hex_source.read_bytes()).hexdigest(),
              'new_parts': [p[1] for p in parts],
              'electrical_runtime_verified': False,
              'audio_heard_verified': False}
    (OUT / 'structural-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (OUT / 'circuit-components.json').write_text(json.dumps(reopened.components(), indent=2), encoding='utf-8')
    (OUT / 'circuit-terminals.json').write_text(json.dumps(reopened._terminals, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    run()

"""Build native Proteus 8 project files; UI verification is performed separately.

Uses the reviewed MIT-licensed proteus-automatic-api file-editing code only.
No Session/native process hooks or third-party UI automation are used.
"""
from pathlib import Path
import sys, json

HERE=Path(__file__).resolve().parent
ROOT=Path(r'D:\Program Files (x86)\Labcenter Electronics\Proteus 8 Professional')
sys.path.insert(0,str(HERE/'tools'/'proteus-api'/'api'))
import component_codec as cc
import device_library as dl
cc.SOURCE=ROOT/'DATA'/'SAMPLES'/'Graph Based Simulation'/'Rescap.pdsprj'
OriginalLibrary=dl.Library
class InstalledLibrary(OriginalLibrary):
    def __init__(self,directory=ROOT/'DATA'/'LIBRARY'):
        super().__init__(directory)
dl.Library=InstalledLibrary

c=cc.Circuit(cc.SOURCE)
donor=HERE/'Ultrasonic_LCD1602.pdsprj'
c.import_from_project(donor,'SRF04')
for name,library in [('AT89C52',None),('LM016L',None),('CRYSTAL','DEVICE'),
                     ('RESPACK-8','DEVICE'),('POT-HG',None),('BUTTON',None),('CAP-ELEC','DEVICE')]:
    c.import_device(name,library=library)

def mm(v): return int(round(v*100000))
def add(device,ref,value,x,y,rotation=0,properties=None):
    c.add(device,ref,value,mm(x),mm(y),rotation=rotation,properties=properties)

add('AT89C52','U1','AT89C52',-30,25,properties={'CLOCK':'11.0592MHz','PROGRAM':'Ultrasonic_LCD1602.hex','X2':'0'})
add('LM016L','LCD1','LCD1602',50,75)
add('SRF04','US1','SRF04',-100,-20,properties={'SETPOINT':'20','MIN':'2','MAX':'400','CAL':'58','STEP':'1'})
add('RESPACK-8','RP1','10k',40,30.08)
add('CRYSTAL','X1','11.0592MHz',-75,17.38,rotation=90)
add('CAPACITOR','C1','22p',-100,22.46)
add('CAPACITOR','C2','22p',-100,0)
add('RESISTOR','R1','10k',-65,4.68,rotation=270)
add('CAP-ELEC','C3','10u',-85,9.76,rotation=270)
add('BUTTON','SW1','RESET',-85,35)
add('CAPACITOR','C4','100n',70,-20)
add('CAP-ELEC','C5','10u',100,-25.08,rotation=270)
add('POT-HG','RV1','10k',100,60,properties={'SETPOINT':'10','MIN':'0','MAX':'100'})
add('RESISTOR','R3','10k',-65,-45,rotation=270)
c.configure_power({'VCC':5.0,'GND':0.0})

# Hide configuration strings while retaining actual model parameters.
for template in c.templates.values():
    lines=template['properties'].splitlines()
    template['properties']='\n'.join(line if line.startswith('{') else '{'+line+'}' for line in lines if line.strip())+'\n'
    template['show_properties']=False

for part in c._parts:
    template=c.templates[part['device']]
    for key in part['properties']:
        if not any(line.lstrip('{').startswith(key+'=') for line in template['properties'].splitlines()):
            template['properties']+='{'+key+'=}\n'
    ref=part['ref']
    if ref=='U1': offsets={'reference':(mm(1),mm(7)),'value':(mm(1),mm(4))}
    elif ref=='LCD1': offsets={'reference':(mm(-20),mm(13)),'value':(mm(-20),mm(10))}
    elif ref=='RP1': offsets={'reference':(0,mm(7)),'value':(0,mm(4))}
    elif ref=='SW1': offsets={'reference':(0,mm(6)),'value':(0,mm(3))}
    else: offsets={'reference':(mm(3),mm(2)),'value':(mm(3),mm(-1))}
    c.update(ref,label_offsets=offsets)

if '--layout' not in sys.argv:
    def endpoint(s): return tuple(s.split('.',1))
    def link(a,b): c.connect(endpoint(a),endpoint(b))
    def port(kind,name,pin):
        pos=None
        ref,logical=endpoint(pin)
        if kind=='label' and ref=='LCD1':
            target=next(p for p in c.pins(ref) if p['name']==logical)
            x,y=target['position']
            depth=(5.08+3.81*int(logical[1:])) if logical.startswith('D') else {'RS':19.05,'RW':22.86,'E':26.67}[logical]
            pos=(x,y-mm(depth))
        if kind=='label' and ref=='US1':
            target=next(p for p in c.pins(ref) if p['name']==logical)
            x,y=target['position']; pos=(x,y-mm(5.08 if logical=='TR' else 10.16))
        return c.add_terminal(kind,name,endpoint(pin),position=pos)
    def power(pin): port('power','VCC',pin)
    def ground(pin): port('ground','GND',pin)
    # Each named net joins the MCU, LCD and physical pull-up resistor pin.
    # Native terminals keep the drawing legible without a 24-wire crossing bundle.
    for bit in range(8):
        port('label',f'D{bit}',f'U1.P0.{bit}/AD{bit}')
        port('label',f'D{bit}',f'RP1.R{bit+1}')
        port('label',f'D{bit}',f'LCD1.D{bit}')
    power('RP1.C')
    for name,mcu,lcd in [('RS','P2.6/A14','RS'),('RW','P2.5/A13','RW'),('EN','P2.7/A15','E')]:
        port('label','LCD_'+name,'U1.'+mcu)
        port('label','LCD_'+name,'LCD1.'+lcd)
    # Sensor trigger and echo match the proven physical firmware.
    for name,mcu,sensor in [('TRIG','P1.0/T2','TR'),('ECHO','P1.1/T2EX','ECHO')]:
        port('label',name,'U1.'+mcu)
        port('label',name,'US1.'+sensor)
    power('US1.VCC'); ground('US1.GND')
    port('label','ECHO','R3.1'); ground('R3.2')
    power('LCD1.VDD'); ground('LCD1.VSS')
    link('LCD1.VEE','RV1.3')
    power('RV1.2'); ground('RV1.1')
    # Clock, active-high RC/button reset, internal ROM enable.
    for pin in ['U1.XTAL1','X1.2','C1.2']: port('label','XTAL1',pin)
    for pin in ['U1.XTAL2','X1.1','C2.2']: port('label','XTAL2',pin)
    ground('C1.1'); ground('C2.1')
    for pin in ['U1.RST','R1.1','C3.-','SW1.2']: port('label','RESET',pin)
    ground('R1.2'); power('C3.+'); power('SW1.1')
    power('U1.$EA$')
    power('C4.2'); ground('C4.1')
    power('C5.+'); ground('C5.-')
    (HERE/'expected_connections.json').write_text(json.dumps(c.connections(),indent=2),encoding='utf-8')

pins={p['ref']:c.pins(p['ref']) for p in c.components()}
(HERE/'pin_layout.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2),encoding='utf-8')
for ref,ps in pins.items():
    print(ref,[(p['name'],p.get('number'),tuple(round(v/100000,2) for v in p['position'])) for p in ps])

if '--layout' in sys.argv:
    c.save(HERE/'layout_draft.pdsprj',title='Experiment 4 - Ultrasonic LCD1602',overwrite=True)
    print('LAYOUT SAVED')
else:
    project=c.save(HERE/'Experiment4_Ultrasonic_LCD1602.pdsprj',title='Experiment 4 - Ultrasonic LCD1602',overwrite=True)
    print('COMPLETE NETWORK SAVED',project)

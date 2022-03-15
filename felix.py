# this is the original script by Felix
# kept here for reference


import socket
import struct
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('192.168.1.119', 27007))
s.send(b'\x43\x52\x57\x48\x01'.ljust(128, b'\0'))
data = s.recv(132)
(len_response,) = struct.unpack('12xi', data[:16])
data = s.recv(len_response)
(hostname, version) = struct.unpack('8x32s32s', data)
print('Hostname: ' + hostname.decode('ascii'))
print('Running: ' + version.decode('ascii'))

s.send(b'\x43\x52\x57\x48\x02'.ljust(128, b'\0'))
data = s.recv(132)
(len_response,) = struct.unpack('12xi', data[:16])
data = b''
while len(data) < len_response:
  data += s.recv(4096)
data = data[60:]

reached_values = False
sections = list()
while data:
  if not reached_values:
    (hdr1, hdr2, section) = struct.unpack('=II128s', data[:136])
    if hdr1 < 100:
      # this is j a n k y
      reached_values = True
    else:
      section = section.decode('latin_1').strip('\0')
      sections.append({'name': section, 'values': list()})
      data = data[264:]
  if reached_values:
    (i1, i2, i3, label, unit, cur, minn, maxx, avg) = struct.unpack('=III128s128x16sdddd', data[:316])
    label = label.decode('latin_1').strip('\0')
    unit = unit.decode('latin_1').strip('\0')
    sections[i2]['values'].append({
      'label': label,
      'unit': unit,
      'cur': cur,
      'min': minn,
      'max': maxx,
      'avg': avg
    })
    data = data[316:]

for section in sections:
  print(section['name'])
  for val in section['values']:
    print(f"  ⌙ {val['label']} ({val['unit']})")
    print(f"      {val['cur']} / {val['min']} / {val['max']} / {val['avg']}")

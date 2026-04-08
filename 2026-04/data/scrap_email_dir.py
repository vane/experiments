#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from collections import defaultdict

def print_email(fpath, fields, header, fw):
  os.getcwd()
  with open(fpath, 'rb') as f:
    lines = f.readlines()
  data = defaultdict(list)
  for line in lines:
    for field in fields:
      if line.startswith(field):
        data[field.strip(b': ')].append(line.strip()[len(field):])
  for h in header:
    fw.write(b'--'+b'||'.join(data[h])+b',')
  fw.write(fpath.encode('utf8')+b'\n')

if __name__ == '__main__':
  root_dir = sys.argv[1]
  fields = [b'Subject: ', b'From: ', b'Date: ', b'X-Mailer: ', b'To: ']
  with open('report.csv', 'wb+') as fw:
    header = [f.strip(b': ') for f in fields]
    fw.write(b','.join(header)+b',fpath\n')
    for root, dirs, files in os.walk(root_dir):
      for file in files:
        fpath = os.path.join(root, file)
        print(f'file path: {fpath}')
        print_email(fpath, fields, header, fw)

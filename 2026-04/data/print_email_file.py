#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

def print_email(fpath, fields):
  with open(fpath, 'rb') as f:
    lines = f.readlines()
  for line in lines:
    for f in fields:
      if line.startswith(f):
        print(line.strip())

if __name__ == '__main__':
  root_dir = sys.argv[1]
  fields = [b'Subject: ', b'From: ', b'Date: ', b'X-Mailer: ', b'To: ']
  for root, dirs, files in os.walk(root_dir):
    for file in files:
      fpath = os.path.join(root, file)
      print(f'@filepath: {fpath}')
      print_email(fpath, fields)

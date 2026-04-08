#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from collections import defaultdict

import pandas as pd

def print_email(fpath, fields, header, df):
  os.getcwd()
  with open(fpath, 'rb') as f:
    lines = f.readlines()
  data = defaultdict(list)
  for line in lines:
    for field in fields:
      if line.startswith(field):
        data[field.strip(b': ')].append(line.strip()[len(field):])
  data[b'fpath'] = fpath.encode('utf8')
  d = pd.DataFrame([data])
  return pd.concat([df, d])

if __name__ == '__main__':
  root_dir = sys.argv[1]
  fields = [b'Subject: ', b'From: ', b'Date: ', b'X-Mailer: ', b'To: ']
  header = [f.strip(b': ') for f in fields]
  df = pd.DataFrame()
  try:
    for root, dirs, files in os.walk(root_dir):
      for file in files:
        fpath = os.path.join(root, file)
        print(f'file path: {fpath}')
        df = print_email(fpath, fields, header, df)
  finally:
    df.to_parquet('report.parquet')

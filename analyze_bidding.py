# -*- coding: utf-8 -*-
import pandas as pd
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

file_path = r'e:\E\任务\task-platform\bidding.xlsx'

# Read each sheet
xl = pd.ExcelFile(file_path)
print(f"Sheets: {xl.sheet_names}")

for sheet in xl.sheet_names:
    print(f"\n\n========== {sheet} ==========\n")
    df = pd.read_excel(file_path, sheet_name=sheet, header=None)
    print(f"Shape: {df.shape}")
    # Print all non-empty rows
    for i, row in df.iterrows():
        row_str = '\t'.join([str(v) for v in row if pd.notna(v)])
        if row_str.strip():
            print(f"R{i+1}: {row_str}")
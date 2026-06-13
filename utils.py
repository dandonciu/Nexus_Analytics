import re
import pandas as pd

# Definirea matricei de conversie
PACKAGING_FACTORS = {
    "BKTp721": 48,      # 48 cutii per palet pentru BKTp721
    "default": 64       # 64 cutii per palet pentru restul produselor
}

def get_factor(code):
    return PACKAGING_FACTORS.get(code, PACKAGING_FACTORS['default'])

def unify_products(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    df['code'] = df['code'].astype(str).str.strip()
    
    # Identificare tolerantă cu Regex
    is_pallet = df['code'].str.contains(r'(?i)^PAL[\s\-_]*', regex=True, na=False)
    df['base_code'] = df['code'].str.replace(r'(?i)^PAL[\s\-_]*', '', regex=True)
    
    factors = df['base_code'].apply(get_factor)
    df.loc[is_pallet, 'stock'] = df.loc[is_pallet, 'stock'] * factors[is_pallet]
    
    df_clean = df.sort_values(by='code', key=lambda x: x.str.contains(r'(?i)^PAL[\s\-_]*', regex=True))
    df_grouped = df_clean.groupby('base_code').agg({
        'product': 'first',
        'stock': 'sum',
        'unit': 'first',
        'category': 'first'
    }).reset_index()
    
    df_grouped.rename(columns={'base_code': 'code'}, inplace=True)
    return df_grouped

def unify_transactions(df, code_column='product_code'):
    if df is None or df.empty:
        return df
    df = df.copy()
    df[code_column] = df[code_column].astype(str).str.strip()
    
    is_pallet = df[code_column].str.contains(r'(?i)^PAL[\s\-_]*', regex=True, na=False)
    df['base_code'] = df[code_column].str.replace(r'(?i)^PAL[\s\-_]*', '', regex=True)
    
    factors = df['base_code'].apply(get_factor)
    df.loc[is_pallet, 'quantity'] = df.loc[is_pallet, 'quantity'] * factors[is_pallet]
    
    df[code_column] = df['base_code']
    df.drop(columns=['base_code'], inplace=True, errors='ignore')
    return df

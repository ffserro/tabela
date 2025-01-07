import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date as dt, timedelta as td

import holidays

st.title('TABELONA')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

# EFETIVO DOS QUE CONCORREM A ESCALA
st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB')
st.session_state.restrito = st.session_state.conn.read(worksheet='REST')

ano = 2025
meses = ['-', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

datas = [dt(ano, 1, 1) + td(i) for i in range(365)]
# datas = [i.strftime('%d/%m/%Y') for i in datas]

feriados = holidays.Brazil()['{}-01-01'.format(ano): '{}-12-31'.format(ano)] + [dt(ano, 6, 11), dt(ano, 12, 13)]

vermelha, preta = [], []

for d in datas:
    if (d.weekday() in (5,6)) or (d in feriados):
        vermelha.append(d)
    else:
        preta.append(d)

for d in vermelha:
    if (d + td(2) in vermelha) and (d + td(1) not in vermelha):
        vermelha.append(d + td(1))
        preta.remove(d + td(1))

vermelha.sort()

efetivo = st.session_state.efetivo
efetivo['EMBARQUE'] = pd.to_datetime(efetivo['EMBARQUE'], dayfirst=True)
efetivo['DESEMBARQUE'] = pd.to_datetime(efetivo['DESEMBARQUE'], dayfirst=True)

restrito = st.session_state.restrito
restrito['INICIAL'] = pd.to_datetime(restrito['INICIAL'], dayfirst=True)
restrito['FINAL'] = pd.to_datetime(restrito['FINAL'], dayfirst=True)

st.write(efetivo)

def get_disponivel(data, efetivo, restrito):
    disp = list(efetivo.NOME.values)
    for i in efetivo[(efetivo.EMBARQUE > data) | (efetivo.DESEMBARQUE <= data)].NOME.values:
        disp.remove(i)
    for i in restrito[(restrito.INICIAL >= data) | (restrito.FINAL <= data)].NOME.unique():
        if i in disp:
            disp.remove(i)
    
    return disp
    

esc_preta = {i:'' for i in preta}
esc_vermelha = {i:'' for i in vermelha}

esc_preta[dt(2025, 1, 6)] = 'CT(IM) Sêrro'
esc_vermelha[dt(2025, 1, 1)] = 'CT Felipe Gondim'

for d in esc_preta:
    esc = get_disponivel(d, efetivo, restrito)
    esc = esc + [esc[0]]
    esc_preta[d] = esc[esc.index(esc_preta[d-td(1)]) + 1]

for d in esc_vermelha:
    esc = get_disponivel(d, efetivo, restrito)
    esc_preta[d] = esc[esc.index(esc_preta[d-td(1)]) - 1]

st.write(esc_preta)

# for m in range(1, 13):
#     df = pd.DataFrame({'DIA':[d for d in datas if d.month == m],
#                         'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == m],
#                         'NOME':['' for d in datas if d.month == m]})
#     st.session_state[meses[m]] = st.session_state.conn.update(worksheet=meses[m], data=df)

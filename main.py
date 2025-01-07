import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date as dt, timedelta as td

import holidays

st.title('TABELONA')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

# EFETIVO DOS QUE CONCORREM A ESCALA
st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB')

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

st.write(st.session_state.efetivo)

esc_preta = {}
esc_vermelha = {}

# for m in range(1, 13):
#     df = pd.DataFrame({'DIA':[d for d in datas if d.month == m],
#                         'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == m],
#                         'NOME':['' for d in datas if d.month == m]})
#     st.session_state[meses[m]] = st.session_state.conn.update(worksheet=meses[m], data=df)

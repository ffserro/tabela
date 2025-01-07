import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime as dt, timedelta as td
from dateutil import tz

tzinfo = tz.gettz('America/Sao_Paulo')

st.title('TABELONA')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

# EFETIVO DOS QUE CONCORREM A ESCALA
st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB')

ano = 2025
meses = ['-', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

datas = [dt(ano, 1, 1) + td(i) for i in range(365)]
datas = [i.strftime('%d/%m/%Y') for i in datas]

feriados = holidays.Brazil()['{}-01-01'.format(ano): '{}-12-31'.format(ano)]

st.write(feriados)
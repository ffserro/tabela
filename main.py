import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date as dt, timedelta as td
from calendar import monthrange

import holidays

st.title('TABELONA DO 💡')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

# EFETIVO DOS QUE CONCORREM A ESCALA
st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB')
st.session_state.restrito = st.session_state.conn.read(worksheet='REST')
st.session_state.licpag = st.session_state.conn.read(worksheet='LICPAG')

licpag = st.session_state.licpag
licpag['DATA'] = pd.to_datetime(licpag['DATA'], dayfirst=True).dt.date

efetivo = st.session_state.efetivo
efetivo['EMBARQUE'] = pd.to_datetime(efetivo['EMBARQUE'], dayfirst=True).dt.date
efetivo['DESEMBARQUE'] = pd.to_datetime(efetivo['DESEMBARQUE'], dayfirst=True).dt.date

restrito = st.session_state.restrito
restrito['INICIAL'] = pd.to_datetime(restrito['INICIAL'], dayfirst=True).dt.date
restrito['FINAL'] = pd.to_datetime(restrito['FINAL'], dayfirst=True).dt.date

ano = 2025
meses = ['-', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

datas = [dt(ano, 1, 1) + td(i) for i in range(365)]

action = st.selectbox('Qual ação você deseja executar?', ['', 'Troca de serviço', 'Adicionar indisponibilidades', 'Alterar data da LicPag', 'Embarque', 'Desembarque'])

if action == 'Adicionar indisponibilidades':
    st.write('Joga aí pra gente:')
    mil_ind = st.selectbox('Militar com indisponibilidade:', ['-'] + list(efetivo.NOME.values))
    per_ind = st.date_input('Período:', [dt.today(), dt.today()], min_value=dt(ano, 1, 1), max_value=dt(ano, 12, 1), format='DD/MM/YYYY')
    mot_ind = st.selectbox('Motivo:', options=['Férias', 'Dispensa médica', 'Destaque', 'Viagem', 'Luto', 'Desembarque', 'Paternidade', 'Qualificando'])
    send_ind = st.button('Enviar')
    if send_ind and mil_ind != '-':
        restrito = pd.concat([restrito, pd.DataFrame({'NOME':[mil_ind], 'INICIAL':[per_ind[0]], 'FINAL':[per_ind[1]], 'MOTIVO':[mot_ind]})])
        st.session_state.conn.update(worksheet='REST', data=restrito)

if action == 'Alterar data da LicPag':
    mes_alt = st.selectbox('Mês da alteração:', ['-'] + list(licpag.MES))
    data_alt = st.date_input('Data da LicPag:', min_value=dt(ano, meses.index(mes_alt), 1), max_value=dt(ano, meses.index(mes_alt), calendar.monthrange(ano, meses.index(mes_alt))[-1]), format='DD/MM/YYYY')
    send_alt = st.button('Enviar')
    if send_alt and mes_alt != '-':
        licpag.loc[licpag.MES==mes_alt, 'DATA'] = data_alt
        st.session_state.conn.update(worksheet='LICPAG', data=licpag)

if action == 'Embarque':
    nome_emb = st.text_input('Nome do embarcado:')
    comimsup_emb = st.select_box('Quem é o ComImSup do velha guarda?', )
    data_emb = st.date_input('Data do embarque:', dt.today(), min_value=dt(ano, 1, 1), max_value=dt(ano, 12, 1), format='DD/MM/YYYY')
    emb_ind = efetivo[efetivo.NOME==comimsup_emb].index + 1
    efetivo = pd.concat([efetivo.iloc[:emb_ind], pd.DataFrame({'NOME':[nome_emb], 'EMBARQUE':[data_emb], 'DESEMBARQUE':[dt(ano+1, 1, 1)]})])
    st.session_state.conn.update(worksheet='EMB', data=efetivo)
    
if action == 'Desembarque':
    nome_dbq = st.selectbox('Quem desembarca?', ['-'] + list(efetivo.NOME))
    data_dbq = st.date_input('Data do desembarque:', dt.today(), min_value=dt(ano, 1, 1), max_value=dt(ano, 12, 1), format='DD/MM/YYYY')
    efetivo.loc[efetivo.NOME==nome_dbq, 'DESEMBARQUE'] = data_dbq
    st.session_state.conn.update(worksheet='EMB', data=efetivo)
    
feriados = holidays.Brazil()['{}-01-01'.format(ano): '{}-12-31'.format(ano)] + [dt(ano, 6, 11), dt(ano, 12, 13)]

vermelha, preta = [], []

for d in datas:
    if (d.weekday() in (5,6)) or (d in feriados) or (d in st.session_state.licpag.DATA.values):
        vermelha.append(d)
    else:
        preta.append(d)

for d in vermelha:
    if (d + td(2) in vermelha) and (d + td(1) not in vermelha):
        vermelha.append(d + td(1))
        preta.remove(d + td(1))

vermelha.sort()

def get_disponivel(data, efetivo, restrito):
    disp = list(efetivo.NOME.values)
    for i in efetivo[(efetivo.EMBARQUE > data) | (efetivo.DESEMBARQUE <= data)].NOME.values:
        disp.remove(i)
    for i in restrito[(restrito.INICIAL <= data) & (restrito.FINAL >= data)].NOME.unique():
        if i in disp:
            disp.remove(i)
    
    return disp
    

esc_preta = pd.DataFrame({'DATA':preta})
esc_vermelha = pd.DataFrame({'DATA':vermelha})

esc_preta.loc[esc_preta.DATA == dt(2025, 1, 6), 'NOME'] = 'CT(IM) Sêrro'
esc_vermelha.loc[esc_vermelha.DATA == dt(2025, 1, 1), 'NOME'] = 'CT Felipe Gondim'

esc_preta.set_index('DATA', inplace=True)
esc_vermelha.set_index('DATA', inplace=True)

for d in esc_preta.index[1:]:
    esc = get_disponivel(d, efetivo, restrito)
    esc = esc + [esc[0]]
    esc_preta.loc[d, 'NOME'] = esc[esc.index(esc_preta.loc[preta[preta.index(d) - 1], 'NOME']) + 1]

for d in esc_vermelha.index[1:]:
    esc = get_disponivel(d, efetivo, restrito)
    esc_vermelha.loc[d, 'NOME'] = esc[esc.index(esc_vermelha.loc[vermelha[vermelha.index(d) - 1], 'NOME']) - 1]

geral_corrida = pd.concat([esc_preta, esc_vermelha]).sort_index()

if action == 'Troca de serviço':
    de = st.date_input('De:', dt.today())
    para = st.date_input('Para:', dt.today())
    motivo_troca = st.text_input('Motivo da troca:')

st.write(geral_corrida)

# for m in range(1, 13):
#     df = pd.DataFrame({'DIA':[d for d in datas if d.month == m],
#                         'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == m],
#                         'NOME':['' for d in datas if d.month == m]})
#     st.session_state[meses[m]] = st.session_state.conn.update(worksheet=meses[m], data=df)

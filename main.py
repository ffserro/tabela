import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date as dt, timedelta as td
from calendar import monthrange

import holidays

st.title('TABELONA DO 💡')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)
st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB')
st.session_state.restrito = st.session_state.conn.read(worksheet='REST')
st.session_state.licpag = st.session_state.conn.read(worksheet='LICPAG')
st.session_state.troca = st.session_state.conn.read(worksheet='TROCA')


troca = st.session_state.troca.copy()

licpag = st.session_state.licpag.copy()
licpag['DATA'] = pd.to_datetime(licpag['DATA'], dayfirst=True).dt.date

efetivo = st.session_state.efetivo.copy()
efetivo['EMBARQUE'] = pd.to_datetime(efetivo['EMBARQUE'], dayfirst=True).dt.date
efetivo['DESEMBARQUE'] = pd.to_datetime(efetivo['DESEMBARQUE'], dayfirst=True).dt.date

restrito = st.session_state.restrito.copy()
restrito['INICIAL'] = pd.to_datetime(restrito['INICIAL'], dayfirst=True).dt.date
restrito['FINAL'] = pd.to_datetime(restrito['FINAL'], dayfirst=True).dt.date

ano = 2025
meses = ['-', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

datas = [dt(ano, 1, 1) + td(i) for i in range(365)]

action = st.selectbox('Qual ação você deseja executar?', ['', 'Troca de serviço', 'Adicionar indisponibilidades', 'Alterar data da LicPag', 'Embarque', 'Desembarque'])

if action == 'Adicionar indisponibilidades':
    mil_ind = st.selectbox('Militar com indisponibilidade:', ['-'] + list(efetivo.NOME.values))
    per_ind = st.date_input('Período:', [dt.today(), dt.today()], min_value=dt(ano, 1, 1), max_value=dt(ano, 12, 1), format='DD/MM/YYYY')
    mot_ind = st.selectbox('Motivo:', options=['Férias', 'Dispensa médica', 'Destaque', 'Viagem', 'Luto', 'Desembarque', 'Paternidade', 'Qualificando'])
    send_ind = st.button('Enviar')
    if send_ind and mil_ind != '-':
        restrito = pd.concat([restrito, pd.DataFrame({'NOME':[mil_ind], 'INICIAL':[per_ind[0]], 'FINAL':[per_ind[1]], 'MOTIVO':[mot_ind]})])
        restrito = restrito.sort_values(by='INICIAL')
        st.rerun()

if action == 'Alterar data da LicPag':
    mes_alt = st.selectbox('Mês da alteração:', meses)
    if mes_alt != '-':
        data_alt = st.date_input('Data da LicPag:', min_value=dt(ano, meses.index(mes_alt), 1), max_value=dt(ano, meses.index(mes_alt), monthrange(ano, meses.index(mes_alt))[-1]), format='DD/MM/YYYY')
        send_alt = st.button('Enviar')
        if send_alt and mes_alt:
            licpag.loc[licpag.MES==mes_alt, 'DATA'] = data_alt
            st.rerun()
            

if action == 'Embarque':
    nome_emb = st.text_input('Nome do embarcado:')
    comimsup_emb = st.selectbox('Quem é o ComImSup do velha guarda?', list(efetivo.NOME))
    data_emb = st.date_input('Data do embarque:', dt.today(), min_value=dt(ano, 1, 1), max_value=dt(ano, 12, 1), format='DD/MM/YYYY')
    emb_ind = efetivo[efetivo.NOME==comimsup_emb].index + 1
    if st.button('Enviar'):
        efetivo = pd.concat([efetivo.iloc[:emb_ind], pd.DataFrame({'NOME':[nome_emb], 'EMBARQUE':[data_emb], 'DESEMBARQUE':[dt(ano+1, 1, 1)]})])
        st.rerun()
    
if action == 'Desembarque':
    nome_dbq = st.selectbox('Quem desembarca?', ['-'] + list(efetivo.NOME))
    data_dbq = st.date_input('Data do desembarque:', dt.today(), min_value=dt(ano, 1, 1), max_value=dt(ano, 12, 1), format='DD/MM/YYYY')
    if st.button('Enviar'):
        efetivo.loc[efetivo.NOME==nome_dbq, 'DESEMBARQUE'] = data_dbq
        st.rerun()
        
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
    st.write(esc[esc.index(esc_preta.loc[preta[preta.index(d) - 1], 'NOME']) + 1])
    esc_preta.loc[d, 'NOME'] = esc[esc.index(esc_preta.loc[preta[preta.index(d) - 1], 'NOME']) + 1]

for d in esc_vermelha.index[1:]:
    esc = get_disponivel(d, efetivo, restrito)
    esc_vermelha.loc[d, 'NOME'] = esc[esc.index(esc_vermelha.loc[vermelha[vermelha.index(d) - 1], 'NOME']) - 1]

geral_corrida = pd.concat([esc_preta, esc_vermelha]).sort_index()

conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}

for nome in conflitos:
    ps = []
    for i in range(len(conflitos[nome])-1):
        a, b = conflitos[nome][i], conflitos[nome][i + 1]
        if b - a <= td(2):
            ps.append((a, b))
    conflitos[nome] = ps

while any(len(conflitos[nome]) > 0 for nome in conflitos):
    for nome in conflitos:
        for conflito in conflitos[nome]:
            ver = conflito[0] if conflito[0] in vermelha else conflito[1]
            pre = conflito[1] if conflito[1] in preta else conflito[0]
    
            if pre < ver:
                geral_corrida.loc[pre], geral_corrida.loc[preta[preta.index(pre) - 2]] = geral_corrida.loc[preta[preta.index(pre) - 2]], geral_corrida.loc[pre]
                troca = pd.concat([troca, pd.DataFrame({'DE':[pre], 'PARA':[preta[preta.index(pre) - 2]], 'MOTIVO':['AUTOMÁTICA']})])
            else:
                geral_corrida.loc[pre], geral_corrida.loc[preta[preta.index(pre) + 2]] = geral_corrida.loc[preta[preta.index(pre) + 2]], geral_corrida.loc[pre]
                troca = pd.concat([troca, pd.DataFrame({'DE':[pre], 'PARA':[preta[preta.index(pre) + 2]], 'MOTIVO':['AUTOMÁTICA']})])
    
    conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}
    
    for nome in conflitos:
        ps = []
        for i in range(len(conflitos[nome])-1):
            a, b = conflitos[nome][i], conflitos[nome][i + 1]
            if b - a <= td(2):
                ps.append((a, b))
        conflitos[nome] = ps

if efetivo != st.session_state.efetivo:
    st.session_state.conn.update(worksheet='EMB', data=efetivo)
if restrito != st.session_state.restrito:
    st.session_state.conn.update(worksheet='REST', data=restrito)
if troca != st.session_state.troca:
    st.session_state.conn.update(worksheet='TROCA', data=troca)
if licpag != st.session_state.licpag:
    st.session_state.conn.update(worksheet='LICPAG', data=licpag)

if action == 'Troca de serviço':
    de = st.date_input('De:', dt.today())
    para = st.date_input('Para:', dt.today())
    motivo_troca = st.text_input('Motivo da troca:')
    geral_corrida.loc[de], geral_corrida.loc[para] = geral_corrida.loc[para], geral_corrida.loc[de]
    troca = pd.concat([troca, pd.DataFrame({'DE':[de], 'PARA':[para], 'MOTIVO':[motivo_troca]})])
    st.session_state.conn.update(worksheet='TROCA', data=troca)

st.write(licpag)

st.divider()

gera_mes = meses.index(st.selectbox('Gerar tabela do mês:', meses))
# if gera_mes != 0:
    # st.write(geral_corrida.index.dt.month==gera_mes)
if st.button('Gerar!') and gera_mes != 0:
    df = pd.DataFrame({'DIA': [d for d in datas if d.month == gera_mes], 'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == gera_mes], 'NOME':[geral_corrida.loc[d][0] for d in datas if d.month == gera_mes]})
    st.write(df)
    st.session_state.conn.update(worksheet=meses[gera_mes], data=df)
# for m in range(1, 13):
#     df = pd.DataFrame({'DIA':[d for d in datas if d.month == m],
#                         'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == m],
#                         'NOME':['' for d in datas if d.month == m]})
#     st.session_state[meses[m]] = st.session_state.conn.update(worksheet=meses[m], data=df)

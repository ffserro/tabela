import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date as dt, timedelta as td
from calendar import monthrange

import holidays

st.title('TABELONA DO 💡')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

def troca_update():
    st.session_state.troca = st.session_state.conn.read(worksheet='TROCA', ttl=60)
    st.session_state.troca['DE'] = pd.to_datetime(st.session_state.troca.DE)
    st.session_state.troca['PARA'] = pd.to_datetime(st.session_state.troca.PARA)
    return st.session_state.troca

def licpag_update():
    st.session_state.licpag = st.session_state.conn.read(worksheet='LICPAG', ttl=60)
    st.session_state.licpag['DATA'] = pd.to_datetime(st.session_state.licpag['DATA'], dayfirst=True).dt.date
    return st.session_state.licpag

def efetivo_update():
    st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB', ttl=60)
    st.session_state.efetivo['EMBARQUE'] = pd.to_datetime(st.session_state.efetivo['EMBARQUE'], dayfirst=True).dt.date
    st.session_state.efetivo['DESEMBARQUE'] = pd.to_datetime(st.session_state.efetivo['DESEMBARQUE'], dayfirst=True).dt.date
    return st.session_state.efetivo

def restrito_update():
    st.session_state.restrito = st.session_state.conn.read(worksheet='REST', ttl=60)
    st.session_state.restrito['INICIAL'] = pd.to_datetime(st.session_state.restrito['INICIAL'], dayfirst=True).dt.date
    st.session_state.restrito['FINAL'] = pd.to_datetime(st.session_state.restrito['FINAL'], dayfirst=True).dt.date
    return st.session_state.restrito

ano = 2025
meses = ['-', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

datas = [dt(ano, 1, 1) + td(i) for i in range(365)]

feriados = holidays.Brazil()['{}-01-01'.format(ano): '{}-12-31'.format(ano)] + [dt(ano, 6, 11), dt(ano, 12, 13)]

vermelha, preta = [], []

licpag = licpag_update()
for d in datas:
    if (d.weekday() in (5,6)) or (d in feriados) or (d in licpag.DATA.values):
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

restrito = restrito_update()
efetivo = efetivo_update()
for d in esc_preta.index[1:]:
    ontem = get_disponivel(preta[preta.index(d) - 1], efetivo, restrito)
    hoje = get_disponivel(d, efetivo, restrito)
    hoje = hoje + hoje
    passa = esc_preta.loc[preta[preta.index(d) - 1]][0]
    if passa in hoje:
        esc_preta.loc[d, 'NOME'] = hoje[hoje.index(passa) + 1]
    else:
        esc_preta.loc[d, 'NOME'] = hoje[ontem.index(passa)]

for d in esc_vermelha.index[1:]:
    ontem = get_disponivel(vermelha[vermelha.index(d) - 1], efetivo, restrito)
    hoje = get_disponivel(d, efetivo, restrito)
    passa = esc_vermelha.loc[vermelha[vermelha.index(d) - 1]][0]
    if passa in hoje:
        esc_vermelha.loc[d, 'NOME'] = hoje[hoje.index(passa) - 1]
    else:
        try:
            esc_vermelha.loc[d, 'NOME'] = hoje[ontem.index(passa) - 1]
        except:
            st.write(esc_vermelha.dropna().tail())
            st.write('hoje', d)
            st.write('ontem', d - td(1))
            st.write(ontem)
            st.write(hoje)
            st.write(passa)

geral_corrida = pd.concat([esc_preta, esc_vermelha]).sort_index()

conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}

for nome in conflitos:
    ps = []
    for i in range(len(conflitos[nome])-1):
        a, b = conflitos[nome][i], conflitos[nome][i + 1]
        if b - a <= td(2):
            ps.append((a, b))
    conflitos[nome] = ps

auto = pd.DataFrame({'DE':[], 'PARA':[], 'MOTIVO':[]})
while any(len(conflitos[nome]) > 0 for nome in conflitos):
    ignored = []
    for nome in conflitos:
        for conflito in conflitos[nome]:
            ver = conflito[0] if conflito[0] in vermelha else conflito[1]
            pre = conflito[1] if conflito[1] in preta else conflito[0]
    
            if pre < ver:
                if any((auto.loc[auto.DE==pre].PARA==preta[preta.index(pre) - 2]).values) or (pre, preta[preta.index(pre) - 2]) in ignored:
                    ignored.append((pre, preta[preta.index(pre) - 2]))
                    continue
                geral_corrida.loc[pre], geral_corrida.loc[preta[preta.index(pre) - 2]] = geral_corrida.loc[preta[preta.index(pre) - 2]], geral_corrida.loc[pre]
                auto = pd.concat([auto, pd.DataFrame({'DE':[pre], 'PARA':[preta[preta.index(pre) - 2]], 'MOTIVO':['AUTOMÁTICA']})])
            else:
                if pre >= dt(ano, 12, 29):
                    ignored.append((pre, pre+td(2)))
                    continue
                elif any((auto.loc[auto.DE==pre].PARA==preta[preta.index(pre) + 2]).values) or (pre, preta[preta.index(pre) + 2]) in ignored:
                    ignored.append((pre, preta[preta.index(pre) + 2]))
                    continue
                geral_corrida.loc[pre], geral_corrida.loc[preta[preta.index(pre) + 2]] = geral_corrida.loc[preta[preta.index(pre) + 2]], geral_corrida.loc[pre]
                auto = pd.concat([auto, pd.DataFrame({'DE':[pre], 'PARA':[preta[preta.index(pre) + 2]], 'MOTIVO':['AUTOMÁTICA']})])

    conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}
    
    for nome in conflitos:
        ps = []
        for i in range(len(conflitos[nome])-1):
            a, b = conflitos[nome][i], conflitos[nome][i + 1]
            if b - a <= td(2):
                ps.append((a, b))
        conflitos[nome] = ps
    
    if len(set(ignored)) == sum([len(conflitos[nome]) for nome in conflitos]):
        for a, b in set(ignored):
            st.write(f'Houve conflito nas trocas automáticas entre os dias {a.strftime('%d/%m')} e {b.strftime('%d/%m')}')
        break

st.session_state.conn.update(worksheet='TROCA_AUT', data=auto.drop_duplicates())

troca = troca_update()

st.write(geral_corrida.index.dtype)
st.write(troca.DE.dtype)
for i, row in troca.iterrows():
    de = row.DE
    para = row.PARA
    geral_corrida.loc[de], geral_corrida.loc[para] = geral_corrida.loc[para], geral_corrida.loc[de]


with st.form('Trocas', clear_on_submit=True):
    st.write('Realizar trocas de serviço:')
    de = st.date_input('De:', dt.today())
    para = st.date_input('Para:', dt.today())
    motivo_troca = st.text_input('Motivo da troca:')
    geral_corrida.loc[de], geral_corrida.loc[para] = geral_corrida.loc[para], geral_corrida.loc[de]
    if st.form_submit_button('Enviar'):
        troca = pd.concat([troca, pd.DataFrame({'DE':[de], 'PARA':[para], 'MOTIVO':[motivo_troca]})])
        st.session_state.conn.update(worksheet='TROCA', data=troca)


st.divider()

gera_mes = meses.index(st.selectbox('Gerar tabela do mês:', meses))
troca['DE'] = pd.to_datetime(troca.DE, dayfirst=True)
trocas_no_mes = troca[(troca.MOTIVO!='AUTOMÁTICA') & (troca.DE.dt.month ==gera_mes)]
if gera_mes != 0 and len(troca[(troca.MOTIVO!='AUTOMÁTICA') & (troca.DE.dt.month == gera_mes)]) > 0:
    st.write(f'Trocas de {["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][gera_mes]}:')
    st.write(troca[(troca.MOTIVO!='AUTOMÁTICA') & (troca.DE.dt.month == gera_mes)])
if st.button('Gerar!') and gera_mes != 0:
    df = pd.DataFrame({'DIA': [d for d in datas if d.month == gera_mes], 'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == gera_mes], 'NOME':[geral_corrida.loc[d][0] for d in datas if d.month == gera_mes]})
    st.write(df)
    st.session_state.conn.update(worksheet=meses[gera_mes], data=df)

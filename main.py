import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date as dt, timedelta as td
from calendar import monthrange

import holidays
from dateutil import tz

tzinfo = tz.gettz('America/Sao_Paulo')

# st.title('TABELONA DO 💡')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

def troca_update():
    st.session_state.troca = st.session_state.conn.read(worksheet='TROCA', ttl=60)
    st.session_state.troca['DE'] = pd.to_datetime(st.session_state.troca.DE, dayfirst=True)
    st.session_state.troca['PARA'] = pd.to_datetime(st.session_state.troca.PARA, dayfirst=True)
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
    st.session_state.restrito.loc[st.session_state.restrito.MOTIVO=='Férias', 'INICIAL'] = st.session_state.restrito.loc[st.session_state.restrito.MOTIVO=='Férias', 'INICIAL'] - td(days=1)
    st.session_state.restrito.loc[st.session_state.restrito.MOTIVO=='Férias', 'FINAL'] = st.session_state.restrito.loc[st.session_state.restrito.MOTIVO=='Férias', 'FINAL'] + td(days=1)
    st.session_state.restrito.loc[st.session_state.restrito.MOTIVO=='Viagem', 'FINAL'] = st.session_state.restrito.loc[st.session_state.restrito.MOTIVO=='Viagem', 'FINAL'] + td(days=1)
    return st.session_state.restrito

ano = 2025
meses = ['-', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

datas = [dt(ano, 1, 1) + td(i) for i in range(365)]

#######
# datas = [i for i in datas if i.month in (dt.today().month, (dt.today().month-1)%12+1)]

feriados = holidays.Brazil()['{}-01-01'.format(ano): '{}-12-31'.format(ano)] + [dt(ano, 6, 11), dt(ano, 12, 13)]

vermelha, preta = [], []

licpag = licpag_update()
for d in datas:
    #  final de semana           feriados           licpag
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

def que_se_segue(passa, efetivo, hoje, tabela):
    efetivos = list(efetivo.NOME.values)
    if tabela == 'p':
        efetivos = efetivos[::-1]
    for i in range(1, len(efetivos)):
        cara = efetivos[efetivos.index(passa) - i]
        if cara in hoje:
            return cara
    

esc_preta = pd.DataFrame({'DATA':preta})
esc_vermelha = pd.DataFrame({'DATA':vermelha})

esc_preta.loc[esc_preta.DATA == dt(2025, 1, 6), 'NOME'] = '1T Brenno Carvalho'
esc_vermelha.loc[esc_vermelha.DATA == dt(2025, 1, 1), 'NOME'] = 'CT(IM) Sêrro'



esc_preta.set_index('DATA', inplace=True)
esc_vermelha.set_index('DATA', inplace=True)

restrito = restrito_update()
efetivo = efetivo_update()
# st.write(list(efetivo.NOME.values))
# st.write(list(efetivo.NOME.values)[::-1])
for d in esc_preta.index[1:]:
    ontem = get_disponivel(preta[preta.index(d) - 1], efetivo, restrito)
    hoje = get_disponivel(d, efetivo, restrito)
    hoje = hoje + hoje
    passa = esc_preta.loc[preta[preta.index(d) - 1]].iloc[0]

    try:
        esc_preta.loc[d, 'NOME'] = que_se_segue(passa, efetivo, hoje, 'p')
    except Exception as e:
        st.write(e)
        pass
    
    #if passa in hoje:
    #    esc_preta.loc[d, 'NOME'] = hoje[hoje.index(passa) + 1]
    #else:
    #    esc_preta.loc[d, 'NOME'] = hoje[ontem.index(passa)]

for d in esc_vermelha.index[1:]:
    ontem = get_disponivel(vermelha[vermelha.index(d) - 1], efetivo, restrito)
    hoje = get_disponivel(d, efetivo, restrito)
    passa = esc_vermelha.loc[vermelha[vermelha.index(d) - 1]].iloc[0]

    try:
        esc_vermelha.loc[d, 'NOME'] = que_se_segue(passa, efetivo, hoje, 'v')
    except Exception as e:
        st.write(e)
        pass
    
    #if passa in hoje:
    #    esc_vermelha.loc[d, 'NOME'] = hoje[hoje.index(passa) - 1]
    #else:
    #    try:
    #        # st.write(efetivo)
    #        st.write(d, passa)
    #        st.write(que_se_segue(passa, efetivo, hoje, 'v'))
    #        st.write(hoje)
    #        st.write(ontem)
    #        # esc_vermelha.loc[d, 'NOME'] = hoje[ontem.index(passa) - 1]
    #        esc_vermelha.loc[d, 'NOME']  = que_se_segue(passa, efetivo, hoje, 'v')
    #    except Exception as e:
    #        st.write(e)
    #        pass
            # st.write(esc_vermelha.dropna().tail())
            # st.write('hoje', d)
            # st.write('ontem', d - td(1))
            # st.write(ontem)
            # st.write(hoje)
            # st.write(passa)

# st.write('preta', esc_preta)
# st.write('vermelha', esc_vermelha)

geral_corrida = pd.concat([esc_preta, esc_vermelha]).sort_index()

#conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}

#for nome in conflitos:
#    ps = []
#    for i in range(len(conflitos[nome])-1):
#        a, b = conflitos[nome][i], conflitos[nome][i + 1]
#        if b - a <= td(2):
#            ps.append((a, b))
#    conflitos[nome] = ps

#st.write(conflitos)

# auto = pd.DataFrame({'DE':[], 'PARA':[], 'MOTIVO':[]})
# while any(len(conflitos[nome]) > 0 for nome in conflitos):
#    ignored = []
#    for nome in conflitos:
#        for conflito in conflitos[nome]:
#            ver = conflito[0] if conflito[0] in vermelha else conflito[1]
#            pre = conflito[1] if conflito[1] in preta else conflito[0]
#    
#            if pre < ver:
#                if any((auto.loc[auto.DE==pre].PARA==preta[preta.index(pre) - 2]).values) or (pre, preta[preta.index(pre) - 2]) in ignored:
#                    ignored.append((pre, preta[preta.index(pre) - 2]))
#                    continue
#                geral_corrida.loc[pre], geral_corrida.loc[preta[preta.index(pre) - 2]] = geral_corrida.loc[preta[preta.index(pre) - 2]], geral_corrida.loc[pre]
#                auto = pd.concat([auto, pd.DataFrame({'DE':[pre], 'PARA':[preta[preta.index(pre) - 2]], 'MOTIVO':['AUTOMÁTICA']})])
#            else:
#                if pre >= dt(ano, 12, 29):
#                    ignored.append((pre, pre+td(2)))
#                    continue
#                elif any((auto.loc[auto.DE==pre].PARA==preta[preta.index(pre) + 2]).values) or (pre, preta[preta.index(pre) + 2]) in ignored:
#                    ignored.append((pre, preta[preta.index(pre) + 2]))
#                    continue
#                geral_corrida.loc[pre], geral_corrida.loc[preta[preta.index(pre) + 2]] = geral_corrida.loc[preta[preta.index(pre) + 2]], geral_corrida.loc[pre]
#                auto = pd.concat([auto, pd.DataFrame({'DE':[pre], 'PARA':[preta[preta.index(pre) + 2]], 'MOTIVO':['AUTOMÁTICA']})])

#    conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}
    
#    for nome in conflitos:
#        ps = []
#        for i in range(len(conflitos[nome])-1):
#            a, b = conflitos[nome][i], conflitos[nome][i + 1]
#            if b - a <= td(2):
#                ps.append((a, b))
#        conflitos[nome] = ps
#    
#    if len(set(ignored)) == sum([len(conflitos[nome]) for nome in conflitos]):
#        # for a, b in set(ignored):
#            # st.write(f'Houve conflito nas trocas automáticas entre os dias {a.strftime('%d/%m')} e {b.strftime('%d/%m')}')
#        break

# st.session_state.conn.update(worksheet='TROCA_AUT', data=auto.drop_duplicates())

troca = troca_update()
geral_corrida.index = pd.to_datetime(geral_corrida.index)
for i, row in troca.iterrows():
    troc1 = geral_corrida.loc[row.DE, 'NOME']
    troc2 = geral_corrida.loc[row.PARA, 'NOME']
    geral_corrida.loc[row.DE, 'NOME'] = troc2
    geral_corrida.loc[row.PARA, 'NOME'] = troc1

conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME}
for nome in conflitos:
    ps = []
    for i in range(len(conflitos[nome])-1):
        a, b = conflitos[nome][i], conflitos[nome][i + 1]
        if b - a <= td(2):
            ps.append((a, b))
    conflitos[nome] = ps

def filtra(mes, conflitos):
  novo_conflitos = {}
  for i in conflitos:
    for j in conflitos[i]:
      if j[0].month==mes or j[1].month==mes:
          if i in novo_conflitos.keys():
              novo_conflitos[i+f'_{list(novo_conflitos).count(i)}'] = [x.strftime('%d/%m') for x in j]
          else:
              novo_conflitos[i] = [x.strftime('%d/%m') for x in j]
  return novo_conflitos
    
gera_mes = dt.today().month # meses.index(st.selectbox('Gerar tabela do mês:', meses))


### POROROCA
carnaval = ['CT Tarle', '2T(IM) Soares Costa', 'CT Felipe Gondim', '1T Brenno Carvalho', 'SO-MO Alvarez', 'CT Damasceno', '1T Brenno Carvalho', 'CT(IM) Sêrro', 'CT Belmonte', '2T(IM) Soares Costa']
for i in range(10):
    geral_corrida.loc[pd.to_datetime(dt(2025,2,28) + td(days=i))] = carnaval[i]


df1 = pd.DataFrame({'DIA': [d for d in datas if d.month == gera_mes], 'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == gera_mes], 'NOME':[geral_corrida.loc[pd.to_datetime(d)][0] for d in datas if d.month == gera_mes]})
df2 = pd.DataFrame({'DIA': [d for d in datas if d.month == (gera_mes+1)%12], 'TABELA':['V' if d in vermelha else 'P' for d in datas if d.month == (gera_mes+1)%12], 'NOME':[geral_corrida.loc[pd.to_datetime(d)][0] for d in datas if d.month == (gera_mes+1)%12]})

df1.loc[(df1.DIA >= dt(2025,3,1)) & (df1.DIA <= dt(2025,3,9)), 'TABELA'] = 'R'

if dt.today() in preta:
    retem1 = preta[preta.index(dt.today())+2]
elif dt.today() in vermelha:
    retem1 = vermelha[vermelha.index(dt.today()) + 2]

if (dt.today() + td(days=1)) in preta:
    retem2 = preta[preta.index(dt.today() + td(days=1))+2]
elif (dt.today() + td(days=1)) in vermelha:
    retem2 = vermelha[vermelha.index(dt.today() + td(days=1)) + 2]

col1, col2 = st.columns(2)

with col1:
    st.title(f'OSE de {dt.today().strftime('%d/%m')}:')
    st.markdown(f'<h2>{geral_corrida.loc[pd.to_datetime(dt.today())][0]}</h2>', unsafe_allow_html=True)
    st.markdown(f'<h6>Retém: {geral_corrida.loc[pd.to_datetime(retem1)][0]}</h2>', unsafe_allow_html=True)
    st.divider()    
    st.title(f'Tabela de {meses[gera_mes]}')
    df1['DIA'] = pd.to_datetime(df1.DIA).dt.strftime('%d/%m/%Y')
    st.dataframe(df1, hide_index=True, height=1125)
    st.session_state.conn.update(worksheet=meses[gera_mes], data=df1)
    st.write('Conflitos:')
    st.write(pd.DataFrame(filtra(gera_mes, conflitos)).T.rename(columns={0:'DE', 1:'PARA'}))


with col2:
    st.title(f'OSE de {(dt.today() + td(days=1)).strftime('%d/%m')}:')
    st.markdown(f'<h2>{geral_corrida.loc[pd.to_datetime(dt.today() + td(days=1))][0]}</h2>', unsafe_allow_html=True)
    st.markdown(f'<h6>Retém: {geral_corrida.loc[pd.to_datetime(retem2)][0]}</h2>', unsafe_allow_html=True)
    st.divider()  
    st.title(f'Tabela de {meses[(gera_mes+1)%12]}')
    df2['DIA'] = pd.to_datetime(df2.DIA).dt.strftime('%d/%m/%Y')
    st.dataframe(df2, hide_index=True, height=1125)
    st.session_state.conn.update(worksheet=meses[(gera_mes+1)%12], data=df2)
    st.write('Conflitos:')
    st.write(pd.DataFrame(filtra(gera_mes+1, conflitos)).T.rename(columns={0:'DE', 1:'PARA'}))


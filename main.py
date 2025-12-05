import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime as dt, timedelta as td
import calendar

import holidays

ANO_REFERENCIA = dt.today().year
meses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

if 'conn' not in st.session_state:
    st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

def alinhar_para_ano_referencia(data, ano_ref=ANO_REFERENCIA):
    if isinstance(data, dt):
        data = data.date()
    if data.year == ano_ref:
        return data
    try:
        return data.replace(year=ano_ref)
    except ValueError:
        ultimo_dia = calendar.monthrange(ano_ref, data.month)[1]
        return dt(ano_ref, data.month, ultimo_dia).date()

def troca_update():
    troca_df = st.session_state.conn.read(worksheet='TROCA', ttl=60).copy()
    troca_df['DE'] = pd.to_datetime(troca_df.DE, dayfirst=True)
    troca_df['PARA'] = pd.to_datetime(troca_df.PARA, dayfirst=True)
    st.session_state.troca = troca_df
    return troca_df

def licpag_update():
    licpag_df = st.session_state.conn.read(worksheet='LICPAG', ttl=60).copy()
    licpag_df['DATA'] = pd.to_datetime(licpag_df['DATA'], dayfirst=True).dt.date
    st.session_state.licpag = licpag_df
    return licpag_df

def efetivo_update():
    efetivo_df = st.session_state.conn.read(worksheet='EMB', ttl=60).copy()
    efetivo_df['EMBARQUE'] = pd.to_datetime(efetivo_df['EMBARQUE'], dayfirst=True).dt.date
    efetivo_df['DESEMBARQUE'] = pd.to_datetime(efetivo_df['DESEMBARQUE'], dayfirst=True).dt.date
    st.session_state.efetivo = efetivo_df
    return efetivo_df

def pororoca_update():
    pororoca_df = st.session_state.conn.read(worksheet='POROROCA', ttl=60).copy()
    pororoca_df['DATA'] = pd.to_datetime(pororoca_df.DATA, dayfirst=True)
    st.session_state.pororoca = pororoca_df
    return pororoca_df

def restrito_update():
    restrito_df = st.session_state.conn.read(worksheet='REST', ttl=60).copy()
    restrito_df['INICIAL'] = pd.to_datetime(restrito_df['INICIAL'], dayfirst=True).dt.date
    restrito_df['FINAL'] = pd.to_datetime(restrito_df['FINAL'], dayfirst=True).dt.date

    motivo_normalizado = (
        restrito_df['MOTIVO']
        .fillna('')
        .astype(str)
        .str.normalize('NFKD')
        .str.encode('ascii', 'ignore')
        .str.decode('ascii')
        .str.lower()
    )

    restrito_df.loc[motivo_normalizado == 'ferias', 'INICIAL'] -= td(days=1)
    restrito_df.loc[motivo_normalizado == 'viagem', 'FINAL'] += td(days=1)

    st.session_state.restrito = restrito_df
    return restrito_df

def get_disponivel(data, efetivo, restrito, ano_ref):
    data = alinhar_para_ano_referencia(data, ano_ref)

    disp = set(efetivo.NOME.values)
    indisponiveis_embarque = set(
        efetivo[(efetivo.EMBARQUE > data) | (efetivo.DESEMBARQUE <= data)].NOME.values
    )
    indisponiveis_restrito = set(
        restrito[(restrito.INICIAL <= data) & (restrito.FINAL >= data)].NOME.values
    )
    disp.difference_update(indisponiveis_embarque)
    disp.difference_update(indisponiveis_restrito)
    return sorted(disp)

def que_se_segue(passa, ordem, disponiveis):
    efetivos_idx = {nome: idx for idx, nome in enumerate(ordem)}
    if passa not in efetivos_idx:
        return None

    base_idx = efetivos_idx[passa]
    for offset in range(1, len(ordem)):
        candidato = ordem[(base_idx - offset) % len(ordem)]
        if candidato in disponiveis:
            return candidato
    return None

def gera_calendario(ano, licpag, efetivo, restrito, troca, nome_preta_anterior=None, nome_vermelha_anterior=None):
    datas = [ts.date() for ts in pd.date_range(f'{ano}-01-01', f'{ano}-12-31')]
    feriados_extra = {
        dt(ano, 6, 11).date(),
        dt(ano, 12, 13).date(),
        dt(ano, 6, 19).date(),
        dt(ano, 10, 27).date(),
    }
    feriados_base = holidays.Brazil(years=ano)
    feriados = sorted(set(feriados_base.keys()) | feriados_extra)

    licpags = set(licpag.DATA.values)

    vermelha = {d for d in datas if (d.weekday() in (5, 6)) or (d in feriados) or (d in licpags)}
    ponte = {d + td(days=1) for d in vermelha if (d + td(days=2) in vermelha)}
    vermelha |= ponte

    preta = sorted(d for d in datas if d not in vermelha)
    vermelha = sorted(vermelha)
    preta_set = set(preta)
    vermelha_set = set(vermelha)

    esc_preta = pd.DataFrame({'DATA':preta})
    esc_vermelha = pd.DataFrame({'DATA':vermelha})

    esc_preta.set_index('DATA', inplace=True)
    esc_vermelha.set_index('DATA', inplace=True)

    ordem_vermelha = list(efetivo.NOME.values)
    ordem_preta = ordem_vermelha[::-1]

    primeira_preta = preta[0] if preta else None
    primeira_vermelha = vermelha[0] if vermelha else None

    if nome_preta_anterior and primeira_preta:
        esc_preta.loc[primeira_preta, 'NOME'] = que_se_segue(
            nome_preta_anterior, ordem_preta, get_disponivel(primeira_preta, efetivo, restrito, ano)
        )
    if nome_vermelha_anterior and primeira_vermelha:
        esc_vermelha.loc[primeira_vermelha, 'NOME'] = que_se_segue(
            nome_vermelha_anterior, ordem_vermelha, get_disponivel(primeira_vermelha, efetivo, restrito, ano)
        )

    if ano == 2025:
        esc_preta.loc[dt(ano, 1, 6).date(), 'NOME'] = '1T Brenno Carvalho'
        esc_vermelha.loc[dt(ano, 1, 1).date(), 'NOME'] = 'CT(IM) Sêrro'

    if primeira_preta and primeira_preta in esc_preta.index and pd.isna(esc_preta.loc[primeira_preta, 'NOME']):
        base = nome_preta_anterior or ordem_preta[0]
        tentativa = que_se_segue(base, ordem_preta, get_disponivel(primeira_preta, efetivo, restrito, ano))
        if tentativa:
            esc_preta.loc[primeira_preta, 'NOME'] = tentativa
        else:
            disp = get_disponivel(primeira_preta, efetivo, restrito, ano)
            if disp:
                esc_preta.loc[primeira_preta, 'NOME'] = disp[0]

    if primeira_vermelha and primeira_vermelha in esc_vermelha.index and pd.isna(esc_vermelha.loc[primeira_vermelha, 'NOME']):
        base = nome_vermelha_anterior or ordem_vermelha[0]
        tentativa = que_se_segue(base, ordem_vermelha, get_disponivel(primeira_vermelha, efetivo, restrito, ano))
        if tentativa:
            esc_vermelha.loc[primeira_vermelha, 'NOME'] = tentativa
        else:
            disp = get_disponivel(primeira_vermelha, efetivo, restrito, ano)
            if disp:
                esc_vermelha.loc[primeira_vermelha, 'NOME'] = disp[0]

    for idx in range(1, len(preta)):
        d = preta[idx]
        passa = esc_preta.loc[preta[idx - 1]].iloc[0]
        try:
            esc_preta.loc[d, 'NOME'] = que_se_segue(passa, ordem_preta, get_disponivel(d, efetivo, restrito, ano))
        except Exception as e:
            st.write(e)
    
    for idx in range(1, len(vermelha)):
        d = vermelha[idx]
        passa = esc_vermelha.loc[vermelha[idx - 1]].iloc[0]
        try:
            esc_vermelha.loc[d, 'NOME'] = que_se_segue(passa, ordem_vermelha, get_disponivel(d, efetivo, restrito, ano))
        except Exception as e:
            st.write(e)
    

    geral_corrida = pd.concat([esc_preta, esc_vermelha]).sort_index()

    geral_corrida.index = pd.to_datetime(geral_corrida.index)
    for _, row in troca.iterrows():
        if (row.DE in geral_corrida.index) and (row.PARA in geral_corrida.index):
            troc1 = geral_corrida.loc[row.DE, 'NOME']
            troc2 = geral_corrida.loc[row.PARA, 'NOME']
            geral_corrida.loc[row.DE, 'NOME'] = troc2
            geral_corrida.loc[row.PARA, 'NOME'] = troc1

    conflitos = {nome:list(geral_corrida[geral_corrida.NOME==nome].index) for nome in efetivo.NOME.unique()}
    for nome in conflitos:
        conflitos[nome] = sorted(conflitos[nome])
        ps = []
        for i in range(len(conflitos[nome])-1):
            a, b = conflitos[nome][i], conflitos[nome][i + 1]
            if b - a <= td(2):
                ps.append((a, b))
        conflitos[nome] = ps

    df_base = pd.DataFrame(
        {
            'DIA': datas,
            'TABELA': ['V' if d in vermelha_set else 'P' for d in datas],
            'NOME': [geral_corrida.loc[pd.to_datetime(d)].values[0] for d in datas],
        }
    )
    df_base['DIA'] = pd.to_datetime(df_base['DIA'])
    df_base['MES'] = df_base['DIA'].dt.month

    return {
        'df_base': df_base,
        'conflitos': conflitos,
        'geral_corrida': geral_corrida,
        'preta': preta,
        'vermelha': vermelha,
        'preta_set': preta_set,
        'vermelha_set': vermelha_set,
    }

licpag = licpag_update()
restrito = restrito_update()
efetivo = efetivo_update()
troca = troca_update()

calendario_atual = gera_calendario(ANO_REFERENCIA, licpag, efetivo, restrito, troca)
df_base = calendario_atual['df_base']
conflitos = calendario_atual['conflitos']
geral_corrida = calendario_atual['geral_corrida']
preta = calendario_atual['preta']
vermelha = calendario_atual['vermelha']
preta_set = calendario_atual['preta_set']
vermelha_set = calendario_atual['vermelha_set']

ultima_preta_nome = None
ultima_vermelha_nome = None
if preta:
    ultima_preta_nome = geral_corrida.loc[pd.to_datetime(preta[-1])].values[0]
if vermelha:
    ultima_vermelha_nome = geral_corrida.loc[pd.to_datetime(vermelha[-1])].values[0]

def filtra(mes, conflitos):
    novo_conflitos = {}
    for i in conflitos:
        for j in conflitos[i]:
            if j[0].month == mes or j[1].month == mes:
                if i in novo_conflitos.keys():
                    novo_conflitos[i + f'_{list(novo_conflitos).count(i)}'] = [x.strftime('%d/%m') for x in j]
                else:
                    novo_conflitos[i] = [x.strftime('%d/%m') for x in j]
    return novo_conflitos

gera_mes = dt.today().month

geral_corrida.sort_index(inplace=True)

df_base['DIA'] = pd.to_datetime(df_base['DIA'])
df_base['MES'] = df_base['DIA'].dt.month

pororoca = pororoca_update()

for _, row in pororoca.iterrows():
    df_base.loc[df_base.DIA==row.DATA, 'NOME'] = row.NOME
    df_base.loc[df_base.DIA==row.DATA, 'TABELA'] = 'R'

df1 = pd.DataFrame(
    {
        'DIA': df_base.loc[df_base.MES == gera_mes, 'DIA'],
        'TABELA': df_base.loc[df_base.MES == gera_mes, 'TABELA'],
        'NOME': df_base.loc[df_base.MES == gera_mes, 'NOME'],
    }
)
proximo_mes = (gera_mes % 12) + 1
df2_base = df_base
df2_conflitos = conflitos
df2_mes = proximo_mes
if gera_mes == 12:
    calendario_proximo = gera_calendario(
        ANO_REFERENCIA + 1,
        licpag,
        efetivo,
        restrito,
        troca,
        nome_preta_anterior=ultima_preta_nome,
        nome_vermelha_anterior=ultima_vermelha_nome,
    )
    df2_base = calendario_proximo['df_base']
    df2_conflitos = calendario_proximo['conflitos']
    df2_mes = 1
df2 = pd.DataFrame(
    {
        'DIA': df2_base.loc[df2_base.MES == df2_mes, 'DIA'],
        'TABELA': df2_base.loc[df2_base.MES == df2_mes, 'TABELA'],
        'NOME': df2_base.loc[df2_base.MES == df2_mes, 'NOME'],
    }
)

hoje = dt.today().date()
amanha = hoje + td(days=1)

def calcula_retem(data):
    try:
        if data in preta_set:
            tabela = preta
        elif data in vermelha_set:
            tabela = vermelha
        else:
            return None
        return tabela[tabela.index(data) + 2]
    except (ValueError, IndexError):
        return None

retem1 = calcula_retem(hoje)
retem2 = calcula_retem(amanha)

col1, col2 = st.columns(2)

with col1:
    st.title(f"OSE de {dt.today().date().strftime('%d/%m')}:")
    st.markdown(f"<h2>{geral_corrida.loc[pd.to_datetime(dt.today().date())].values[0]}</h2>", unsafe_allow_html=True)
    st.markdown(
        f"<h6>Retém: {geral_corrida.loc[pd.to_datetime(retem1)].values[0] if retem1 else 'N/A'}</h2>",
        unsafe_allow_html=True,
    )
    st.divider()    
    st.title(f'Tabela de {meses[(gera_mes-1)%12]}')
    df1['DIA'] = pd.to_datetime(df1.DIA).dt.strftime('%d/%m/%Y')
    st.dataframe(df1, hide_index=True, height=1125)
    st.session_state.conn.update(worksheet=meses[gera_mes-1], data=df1)
    st.write('Conflitos:')
    st.write(pd.DataFrame(filtra(gera_mes, conflitos)).T.rename(columns={0:'DE', 1:'PARA'}))


with col2:
    st.title(f"OSE de {(dt.today().date() + td(days=1)).strftime('%d/%m')}:")
    st.markdown(f"<h2>{geral_corrida.loc[pd.to_datetime(dt.today().date() + td(days=1))].values[0]}</h2>", unsafe_allow_html=True)
    st.markdown(
        f"<h6>Retém: {geral_corrida.loc[pd.to_datetime(retem2)].values[0] if retem2 else 'N/A'}</h2>",
        unsafe_allow_html=True,
    )
    st.divider()  
    st.title(f'Tabela de {meses[df2_mes - 1]}')
    df2['DIA'] = pd.to_datetime(df2.DIA).dt.strftime('%d/%m/%Y')
    st.dataframe(df2, hide_index=True, height=1125)
    st.session_state.conn.update(worksheet=meses[df2_mes - 1], data=df2)
    st.write('Conflitos:')
    st.write(pd.DataFrame(filtra(df2_mes, df2_conflitos)).T.rename(columns={0:'DE', 1:'PARA'}))
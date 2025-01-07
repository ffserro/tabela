import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime as dt
from dateutil import tz

tzinfo = tz.gettz('America/Sao_Paulo')

st.title('TABELONA')

st.session_state.conn = st.connection('gsheets', type=GSheetsConnection)

st.session_state.efetivo = st.session_state.conn.read(worksheet='EMB')

st.write(st.session_state.efetivo)
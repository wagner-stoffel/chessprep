"""ChessPrep MVP — evidence-based pre-match preparation from public games."""
import pandas as pd
import streamlit as st

from chessprep.api import ChessAPIError, get_recent_games, parse_username
from chessprep.analysis import (
    build_plan, common_paths, parse_games, summary, top_openings, to_markdown
)

st.set_page_config(page_title="ChessPrep | Preparação pré-partida", page_icon="♞", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1200px; padding-top: 2rem;}
[data-testid="stMetric"] {background: #18212e10; border: 1px solid #8293a433; padding: 1rem; border-radius: 12px;}
.small-note {color: #808d9e; font-size: .86rem;}
</style>""", unsafe_allow_html=True)

st.title("♞ ChessPrep")
st.caption("Prepare-se antes de uma partida usando jogos públicos. Ferramenta independente, sem afiliação ao Chess.com.")
with st.form("settings", border=True):
    left, right = st.columns(2)
    with left:
        yours_text = st.text_input("Seu usuário ou link do Chess.com", value="wagnerstoffelnh")
    with right:
        opponent_text = st.text_input("Link do adversário", value="https://www.chess.com/member/yenriva")
    c1, c2, c3 = st.columns(3)
    with c1:
        count = st.selectbox("Partidas recentes por jogador", [20, 50, 100], index=1)
    with c2:
        speed_label = st.selectbox("Modalidade", ["Todas", "Rapid", "Blitz", "Bullet", "Daily"], index=0)
    with c3:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        run = st.form_submit_button("Analisar confronto", type="primary", use_container_width=True)


@st.cache_data(ttl=3600, show_spinner=False)
def collect(username: str, count: int, speed: str):
    return get_recent_games(username, limit=count, time_class=speed)


if run:
    try:
        your_user = parse_username(yours_text)
        opponent = parse_username(opponent_text)
        if your_user == opponent:
            st.error("Escolha dois jogadores diferentes.")
            st.stop()
        speed = speed_label.lower() if speed_label != "Todas" else "all"
        with st.spinner("Consultando arquivos públicos do Chess.com — as requisições são sequenciais..."):
            your_raw = collect(your_user, count, speed)
            opp_raw = collect(opponent, count, speed)
        st.session_state["report"] = (
            your_user, opponent, parse_games(your_raw, your_user), parse_games(opp_raw, opponent),
            your_raw, opp_raw, speed_label,
        )
    except (ChessAPIError, ValueError) as exc:
        st.error(str(exc))
        st.stop()

if "report" not in st.session_state:
    st.info("Informe os perfis, selecione a modalidade e clique em **Analisar confronto**.")
    st.markdown("**O MVP faz análise estatística das partidas concluídas.** Ele não identifica erros de cálculo ou melhores lances: isso exige Stockfish, previsto para a próxima versão.")
    st.stop()

your_user, opponent, your_games, opp_games, your_raw, opp_raw, chosen_speed = st.session_state["report"]

st.subheader(f"{your_user} × {opponent}")
if not your_games or not opp_games:
    st.warning(f"Dados insuficientes na modalidade '{chosen_speed}': você tem {len(your_games)} partida(s) válida(s), e o adversário tem {len(opp_games)}.")
    st.info("Tente 'Todas' as modalidades ou aguarde até que ambos tenham partidas concluídas publicadas.")
    st.stop()

mine, theirs = summary(your_games), summary(opp_games)
a, b, c, d = st.columns(4)
a.metric("Suas partidas", mine["total"])
b.metric("Pontuação sua", f"{mine['score_pct']}%")
c.metric("Partidas do adversário", theirs["total"])
d.metric("Pontuação adversária", f"{theirs['score_pct']}%")
st.caption("Pontuação = (vitórias + ½ empates) / partidas. A estatística depende da seleção de partidas e não mede, isoladamente, força enxadrística.")

st.subheader("Comparação de desempenho")
rows = []
for username, games in [(your_user, your_games), (opponent, opp_games)]:
    for side, side_name in [("white", "Brancas"), ("black", "Pretas")]:
        x = summary(games, side)
        rows.append({"Jogador": username, "Cor": side_name, "Partidas": x["total"],
                     "Vitórias": x["wins"], "Empates": x["draws"], "Derrotas": x["losses"],
                     "Pontuação (%)": x["score_pct"]})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

st.subheader("Plano de preparação")
white_tab, black_tab = st.tabs(["Você joga de brancas", "Você joga de pretas"])
for tab, color in [(white_tab, "white"), (black_tab, "black")]:
    with tab:
        for item in build_plan(your_games, opp_games, color):
            st.markdown("- " + item)
        overlap = common_paths(your_games, opp_games, color)
        st.markdown("**Linhas observadas nos dois históricos**")
        if overlap:
            st.dataframe(pd.DataFrame(overlap), hide_index=True, use_container_width=True)
            st.caption("São coincidências históricas, não previsões nem linhas aprovadas por motor.")
        else:
            st.caption("Não foram encontradas linhas com pelo menos dois meios-lances iguais nos dois históricos filtrados.")

st.subheader("Aberturas mais frequentes")
open_a, open_b = st.columns(2)
for col, username, games in [(open_a, your_user, your_games), (open_b, opponent, opp_games)]:
    with col:
        st.markdown(f"**{username}**")
        color_selection = st.radio("Cor", ["Brancas", "Pretas"], horizontal=True, key=f"opening-{username}")
        rows = top_openings(games, "white" if color_selection == "Brancas" else "black")
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("Sem jogos nesta cor.")

st.subheader("Últimas partidas consultadas")
games_tab_a, games_tab_b = st.tabs([your_user, opponent])
for tab, games in [(games_tab_a, your_games), (games_tab_b, opp_games)]:
    with tab:
        rows = [{"Data (UTC)": g["date"], "Cor": "Brancas" if g["color"] == "white" else "Pretas",
                 "Resultado": g["outcome"], "Abertura": g["opening"], "Lances iniciais": " ".join(g["moves"][:8]),
                 "Partida": g["url"]} for g in games]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                     column_config={"Partida": st.column_config.LinkColumn("Partida")})

st.subheader("Exportar")
md = to_markdown(your_user, opponent, your_games, opp_games)
st.download_button("Baixar relatório (.md)", md.encode("utf-8"),
                   file_name=f"chessprep_{your_user}_vs_{opponent}.md", mime="text/markdown")
with st.expander("Fontes, limitações e uso responsável"):
    st.markdown("""- Fonte: [Chess.com Published Data API](https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it). Somente partidas públicas e concluídas.
- As partidas podem demorar para aparecer devido ao cache do Chess.com. Evitamos consultas paralelas.
- Apenas xadrez padrão é incluído; partidas de Chess960 e outras variantes são ignoradas.
- PGNs ausentes ou inválidos são desconsiderados. Amostras pequenas são indicadores fracos.
- Aberturas podem estar incompletas ou sem classificação no PGN.
- Recomendações são estatísticas e não equivalem a uma análise do Stockfish.
- Use o ChessPrep **antes** de jogar, nunca para receber assistência durante partidas em andamento.
- Projeto independente, sem afiliação com Chess.com. Não utiliza suas marcas, peças ou interfaces proprietárias.""")

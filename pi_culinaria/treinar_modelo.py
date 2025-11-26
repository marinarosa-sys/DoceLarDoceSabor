import pickle
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from bk_usuario import db, Favorito
from bk_receita import Receita, Avaliacao

def treinar_modelo():
    from flask import current_app as app

    with app.app_context():

        # 1) Carregar avaliações (notas)
        avaliacoes = db.session.query(
            Avaliacao.fk_usuario,
            Avaliacao.fk_receita,
            Avaliacao.nota,
            Avaliacao.treinado
        ).all()

        if not avaliacoes:
            print("⚠️ Nenhuma avaliação encontrada. Adicione notas no app.")
            return False

        df = pd.DataFrame(avaliacoes, columns=["usuario", "receita", "nota", "treinado"])

        novas = df[df["treinado"] == False]
        if novas.empty:
            print("⏳ Nenhum dado novo para treinar.")
            return False

        # 2) Criar tabela usuário x receita
        df_filtrado = df.copy()
        df_filtrado.loc[df_filtrado["nota"] <= 2, "nota"] = 0  # notas ruins viram 0

        matriz = df_filtrado.pivot_table(
            index="usuario",
            columns="receita",
            values="nota",
            fill_value=0
        )


        # 3) Similaridade entre receitas usando cosseno
        similaridade = cosine_similarity(matriz.T)
        similaridade_df = pd.DataFrame(similaridade, index=matriz.columns, columns=matriz.columns)

        # ---- Ajustar similaridade com a média das notas ----
        media_por_receita = df_filtrado.groupby("receita")["nota"].mean()
        qualidade = media_por_receita / media_por_receita.max()

        similaridade_df = similaridade_df.mul(qualidade, axis=0).mul(qualidade, axis=1)

        # 4) Categorias favoritas por favoritos
        favoritos = (
            db.session.query(Favorito.fk_usuario, Receita.categoria)
            .join(Receita, Receita.id == Favorito.fk_receita)
            .all()
        )

        preferencias_categoria = {}
        if favoritos:
            fav_df = pd.DataFrame(favoritos, columns=["usuario", "categoria"])
            preferencias_categoria = fav_df.groupby("usuario")["categoria"].agg(lambda x: x.mode()[0]).to_dict()

        # 5) Salvar modelos
        with open("modelo_recomendacao.pkl", "wb") as f:
            pickle.dump(similaridade_df, f)

        with open("preferencias_categorias.pkl", "wb") as f:
            pickle.dump(preferencias_categoria, f)

        with open("media_receitas.pkl", "wb") as f:
            pickle.dump(media_por_receita.to_dict(), f)

        # 6) Atualiza marcação das avaliações
        Avaliacao.query.filter_by(treinado=False).update({Avaliacao.treinado: True})
        db.session.commit()

        print("🤖 Modelo re-treinado com sucesso!")
        return True


# Permite executar pelo terminal
if __name__ == "__main__":
    treinar_modelo()

const menu = document.getElementById('menu');
const btn = document.getElementById('toggle-btn');

btn.addEventListener('click', () => {
  menu.classList.toggle('recolhido');

  // Muda a seta conforme o estado
  if (menu.classList.contains('recolhido')) {
    btn.textContent = '→';
  } else {
    btn.textContent = '←';
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const coracoes = document.querySelectorAll(".coracao");

  coracoes.forEach(coracao => {
    coracao.addEventListener("click", async () => {
      const receitaId = coracao.getAttribute("data-receita-id");
      const card = coracao.closest(".receita-card");

      // Troca o ícone visualmente (cheio → vazio)
      coracao.textContent = "♡";

      try {
        const resposta = await fetch(`/remover_favorito/${receitaId}`, {
          method: "POST"
        });

        if (resposta.ok) {
          // Adiciona uma animação suave antes de remover o card
          card.classList.add("removendo");
          setTimeout(() => card.remove(), 300);
        } else {
          console.error("Erro ao remover favorito:", resposta.status);
        }
      } catch (erro) {
        console.error("Falha na requisição:", erro);
      }
    });
  });
});

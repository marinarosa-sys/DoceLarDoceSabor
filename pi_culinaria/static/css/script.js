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

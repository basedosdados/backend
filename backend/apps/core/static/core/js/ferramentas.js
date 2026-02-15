import { formularios } from './forms.js';

const modal = document.getElementById('ferramentasModal');
const closeButton = modal.querySelector('.close-button');
const toolButtons = modal.querySelectorAll('.tool-btn');
const toolContent = document.getElementById('toolContent');
const loadingOverlay = document.getElementById('loadingOverlay');

function abrirModal() {
  modal.style.display = 'flex';
}

function fecharModal() {
  modal.style.display = 'none';
}

closeButton.onclick = fecharModal;
window.onclick = function(event) {
  if (event.target === modal) {
    fecharModal();
  }
}

toolButtons.forEach(btn => {
  btn.addEventListener('click', () => {

    toolButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const tool = btn.dataset.tool;

    if (formularios[tool]) {
      toolContent.innerHTML = formularios[tool]();
    } else {
      toolContent.innerHTML = "<p>Ferramenta não encontrada.</p>";
    }

  });
});

// Funções de loading
function mostrarCarregamento() { loadingOverlay.style.display = 'block'; }
function esconderCarregamento() { loadingOverlay.style.display = 'none'; }

// Processar formulário dinâmico
function processar(formId) {
  const form = document.getElementById(formId);
  const formData = new FormData(form);
  mostrarCarregamento();

  fetch('/upload_columns/', {
      method: 'POST',
      body: formData,
      headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
  })
  .then(response => response.json())
  .then(data => {
      alert('Dados enviados com sucesso!');
      fecharModal();
  })
  .catch(error => {
      alert('Erro ao enviar dados: ' + error);
  })
  .finally(() => esconderCarregamento());
}


window.abrirModal = abrirModal;
window.fecharModal = fecharModal;

const modal = document.getElementById('dadosModal');
const closeButton = document.querySelector('.close-button');
const dadosForm = document.getElementById('dadosForm');
const loadingOverlay = document.getElementById('loadingOverlay');

function mostrarCarregamento() {
loadingOverlay.style.display = 'block';
}

// Função para esconder a animação de carregamento
function esconderCarregamento() {
loadingOverlay.style.display = 'none';
}

// Função para abrir a modal
function abrirModal() {
modal.style.display = 'block';
}

// Função para fechar a modal
function fecharModal() {
modal.style.display = 'none';
}

// Adicionar botão para abrir a modal
// Event listeners
closeButton.onclick = fecharModal;
window.onclick = function(event) {
if (event.target === modal) {
    fecharModal();
}
}

function processar() {

const formData = new FormData(dadosForm);
mostrarCarregamento();

fetch('/upload_columns/', {
    method: 'POST',
    body: formData,
    headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    }
})
.then(response => response.json())
.then(data => {
    alert('Dados enviados com sucesso!' + data);
    fecharModal();
})
.catch(error => {
    alert('Erro ao enviar dados: ' + error);
})
.finally(() => {
esconderCarregamento(); // Esconde o carregamento independente do resultado
});
};

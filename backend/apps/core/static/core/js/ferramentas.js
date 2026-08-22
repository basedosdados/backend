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
if (event.target === metadadosModal) {
    metadadosModal.style.display = 'none';
}
if (event.target === syncUpdateModal) {
    closeSyncUpdateModal();
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

const metadadosModal = document.getElementById('metadadosModal');
const metadadosCloseButton = document.getElementById('metadadosCloseButton');
const metadadosResultado = document.getElementById('metadadosResultado');

const METADADOS_TIPO_LABELS = {
    somente_bigquery: 'Só no BigQuery',
    somente_api: 'Só na API',
    tipo_diferente: 'Tipo diferente',
    descricao_diferente: 'Descrição diferente',
};

metadadosCloseButton.onclick = function() {
    metadadosModal.style.display = 'none';
}

function renderDiscrepanciaMetadados(discrepancia) {
    const linha = document.createElement('div');
    linha.className = 'metadados-linha';

    const badge = document.createElement('span');
    badge.className = 'metadados-badge metadados-badge--' + discrepancia.tipo;
    badge.textContent = METADADOS_TIPO_LABELS[discrepancia.tipo] || discrepancia.tipo;
    linha.appendChild(badge);

    const coluna = document.createElement('code');
    coluna.className = 'metadados-coluna';
    coluna.textContent = discrepancia.coluna;
    linha.appendChild(coluna);

    if (discrepancia.bigquery !== undefined || discrepancia.api !== undefined) {
        const detalhe = document.createElement('span');
        detalhe.className = 'metadados-detalhe';
        detalhe.textContent = 'BigQuery: ' + (discrepancia.bigquery || '(vazio)') +
            ' → API: ' + (discrepancia.api || '(vazio)');
        linha.appendChild(detalhe);
    }

    return linha;
}

function mostrarResultadoMetadados(data) {
    metadadosResultado.innerHTML = '';

    if (data.erro) {
        const p = document.createElement('p');
        p.className = 'metadados-erro-geral';
        p.textContent = data.erro;
        metadadosResultado.appendChild(p);
    } else if (data.status === 'sucesso') {
        const p = document.createElement('p');
        p.className = 'metadados-sucesso';
        p.textContent = 'Metadados consistentes com o BigQuery.';
        metadadosResultado.appendChild(p);
    } else {
        data.discrepancias.forEach(function(discrepancia) {
            metadadosResultado.appendChild(renderDiscrepanciaMetadados(discrepancia));
        });
    }

    metadadosModal.style.display = 'block';
}

function checarMetadados() {

const formData = new FormData();
formData.append('table_id', document.getElementById('table_id').value);
mostrarCarregamento();

fetch('/admin-tools/check-metadados/', {
    method: 'POST',
    body: formData,
    headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    }
})
.then(response => response.json())
.then(data => {
    mostrarResultadoMetadados(data);
})
.catch(error => {
    alert('Erro ao checar metadados: ' + error);
})
.finally(() => {
esconderCarregamento();
});
};

const syncUpdateModal = document.getElementById('syncUpdateModal');
const syncUpdateCloseButton = document.getElementById('syncUpdateCloseButton');
const syncUpdateResultado = document.getElementById('syncUpdateResultado');
let syncUpdateSucceeded = false;

function closeSyncUpdateModal() {
    syncUpdateModal.style.display = 'none';
    if (syncUpdateSucceeded) {
        location.reload();
    }
}

syncUpdateCloseButton.onclick = closeSyncUpdateModal;

function syncUpdateLatest(tableId, button) {
    if (button && button.disabled) {
        return;
    }

    if (!confirm('Sincronizar a Última Atualização com o last_modified do BigQuery?')) {
        return;
    }

    if (button) {
        button.disabled = true;
    }

    syncUpdateSucceeded = false;
    syncUpdateResultado.innerHTML = '';
    const loading = document.createElement('div');
    loading.className = 'sync-loading';
    const spinner = document.createElement('div');
    spinner.className = 'spinner-small';
    const texto = document.createElement('span');
    texto.textContent = 'Sincronizando com o BigQuery...';
    loading.appendChild(spinner);
    loading.appendChild(texto);
    syncUpdateResultado.appendChild(loading);
    syncUpdateModal.style.display = 'block';

    const formData = new FormData();
    formData.append('table_id', tableId);

    fetch('/admin-tools/sync-update-latest/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        syncUpdateSucceeded = data.status === 'sucesso';
        const p = document.createElement('p');
        p.className = syncUpdateSucceeded ? 'metadados-sucesso' : 'metadados-erro-geral';
        p.textContent = data.mensagem || data.erro;
        syncUpdateResultado.innerHTML = '';
        syncUpdateResultado.appendChild(p);

        if (syncUpdateSucceeded) {
            const aviso = document.createElement('p');
            aviso.className = 'metadados-detalhe';
            aviso.textContent = 'Ao fechar esta janela, a página será atualizada.';
            syncUpdateResultado.appendChild(aviso);
        }
    })
    .catch(error => {
        const p = document.createElement('p');
        p.className = 'metadados-erro-geral';
        p.textContent = 'Erro ao sincronizar: ' + error;
        syncUpdateResultado.innerHTML = '';
        syncUpdateResultado.appendChild(p);
    })
    .finally(() => {
        if (button) {
            button.disabled = false;
        }
    });
}

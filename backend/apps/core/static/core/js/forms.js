export const formularios = {
  importar: () => `
    <form id="importarForm">
      {% csrf_token %}
      <div class="form-group">
          <label for="table_id">Table ID:</label>
          <input type="text" id="table_id" name="table_id"
                 required value="{{ original.pk }}" readonly>
      </div>

      <div class="form-group">
          <label for="dataset_id">Dataset ID:</label>
          <input type="text" id="dataset_id" name="dataset_id"
                 required value="{{ original.dataset_id }}" readonly>
      </div>

      <div class="form-group">
          <label for="link_arquitetura">Link Arquitetura:</label>
          <input type="text" id="link_arquitetura"
                 name="link_arquitetura" required>
      </div>

      <button type="button"
              class="btn btn-sm {{ jazzmin_ui.button_classes.secondary }}"
              onclick="processar('importarForm')">
          Processar
      </button>
    </form>
  `,

  exportar: () => `
    <form id="exportarForm">
      {% csrf_token %}
      <div class="form-group">
          <label for="export_format">Formato:</label>
          <select id="export_format" name="export_format">
            <option value="csv">CSV</option>
            <option value="xlsx">XLSX</option>
          </select>
      </div>

      <button type="button"
              class="btn btn-sm {{ jazzmin_ui.button_classes.secondary }}"
              onclick="processar('exportarForm')">
          Exportar
      </button>
    </form>
  `,

  relatorios: () => `
      <p>Área de relatórios (futuro formulário ou gráfico).</p>
  `,
  dashboard: () => `
    <div style="
      position: relative;
      width: calc(100% - 20px);     /* quase toda largura do modal */
      height: calc(100vh - 120px);   /* um pouco menor que a tela, deixa espaço no topo e embaixo */
      margin-top: 20px;             /* distância do topo do modal */
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 10px;
      box-sizing: border-box;
    ">
      <iframe
        src="https://storage.googleapis.com/basedosdados-dev/elementary_report.html#/report/dashboard"
        style="
          width: 100%;
          height: 100%;
          border: none;
          border-radius: 8px;
          box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        "
      ></iframe>
    </div>
  `
};

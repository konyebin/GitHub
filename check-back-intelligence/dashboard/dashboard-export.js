/**
 * Export in-memory dashboard customer rows (portfolio / data table) to xlsx.
 */
const DashboardExport = (function () {
  function exportColumns(columns) {
    return columns.filter(
      (c) =>
        c &&
        c !== '_biaSlideOnly' &&
        (!String(c).startsWith('_') || c === '_addonsPtu')
    );
  }

  function cellValue(val) {
    if (val == null) return '';
    if (val instanceof Date) return val.toISOString().slice(0, 10);
    return val;
  }

  function rowForExport(row, columns) {
    const out = {};
    columns.forEach((col) => {
      out[col] = cellValue(row[col]);
    });
    return out;
  }

  function filenameFromDisplay(displayName) {
    const base = String(displayName || 'check_back').replace(/\.xlsx?$/i, '');
    return base + '_from_dashboard.xlsx';
  }

  function mergeExportColumns(columns, rows) {
    const cols = exportColumns(columns || []);
    const seen = new Set(cols);
    (rows || []).forEach((row) => {
      Object.keys(row || {}).forEach((k) => {
        if (!k || seen.has(k)) return;
        if (k.startsWith('_') && k !== '_addonsPtu') return;
        seen.add(k);
        cols.push(k);
      });
    });
    return cols;
  }

  function exportCustomerData(rows, columns, displayName) {
    if (typeof XLSX === 'undefined') throw new Error('Spreadsheet library not loaded');
    if (!rows || !rows.length) throw new Error('No customer rows in the dashboard table');
    const workbookRows = rows.filter((r) => !r._biaSlideOnly);
    const exportRows = workbookRows.length ? workbookRows : rows;
    const cols = mergeExportColumns(columns, exportRows);
    if (!cols.length) throw new Error('No columns to export');
    const body = exportRows.map((row) => rowForExport(row, cols));
    const ws = XLSX.utils.json_to_sheet(body, { header: cols });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Customer Data');
    XLSX.writeFile(wb, filenameFromDisplay(displayName));
  }

  return {
    exportColumns,
    mergeExportColumns,
    exportCustomerData,
    filenameFromDisplay,
  };
})();

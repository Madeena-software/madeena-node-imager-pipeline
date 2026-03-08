import { useEffect, useState } from 'react';
import api from '../services/api';

const initialFormState = {
  kategori_grup: '',
  file: null,
};

function CustomNodeUploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [formState, setFormState] = useState(initialFormState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [warnings, setWarnings] = useState([]);

  useEffect(() => {
    if (!isOpen) {
      setFormState(initialFormState);
      setIsSubmitting(false);
      setErrorMessage('');
      setSuccessMessage('');
      setWarnings([]);
    }
  }, [isOpen]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!formState.kategori_grup.trim()) {
      setErrorMessage('Nama grup/kategori wajib diisi.');
      return;
    }

    if (!formState.file) {
      setErrorMessage('Silakan pilih file Python (.py) terlebih dahulu.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');
    setWarnings([]);

    try {
      const response = await api.uploadCustomNode(formState.file, formState.kategori_grup.trim());
      const registeredNodeIds = response.data.registered_node_ids || [];
      const responseWarnings = response.data.warnings || [];

      setWarnings(responseWarnings);
      setSuccessMessage(
        registeredNodeIds.length > 0
          ? `Berhasil mendaftarkan node: ${registeredNodeIds.join(', ')}`
          : 'Custom node berhasil diunggah.'
      );

      await onUploadSuccess?.();
      setFormState(initialFormState);
    } catch (error) {
      const backendMessage =
        error.response?.data?.message ||
        error.response?.data?.error ||
        error.message ||
        'Upload custom node gagal.';
      setErrorMessage(backendMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay">
      <div className="modal custom-node-modal">
        <div className="modal-header">
          <div>
            <h3>Upload Custom Node (.py)</h3>
            <p className="modal-subtitle">
              File akan divalidasi di backend. Jika import atau class node gagal, file akan ditolak
              dan tidak disimpan.
            </p>
          </div>
          <button className="close-button" onClick={onClose} disabled={isSubmitting}>
            ×
          </button>
        </div>

        <form className="modal-content custom-node-form" onSubmit={handleSubmit}>
          <label className="custom-node-field">
            <span>Nama Grup / Kategori</span>
            <input
              type="text"
              value={formState.kategori_grup}
              onChange={(event) =>
                setFormState((prev) => ({ ...prev, kategori_grup: event.target.value }))
              }
              placeholder="Contoh: Experimental, CT Tools, QA"
              disabled={isSubmitting}
            />
          </label>

          <label className="custom-node-field">
            <span>File Python (.py)</span>
            <input
              type="file"
              accept=".py,text/x-python,text/plain"
              onChange={(event) =>
                setFormState((prev) => ({ ...prev, file: event.target.files?.[0] || null }))
              }
              disabled={isSubmitting}
            />
          </label>

          <div className="custom-node-actions-row">
            <a className="template-download-link" href={api.customNodeTemplateUrl()} download>
              Download Template
            </a>
            {formState.file && <span className="selected-file-name">{formState.file.name}</span>}
          </div>

          {errorMessage && (
            <div className="custom-node-feedback custom-node-feedback-error" role="alert">
              <strong>Upload ditolak</strong>
              <pre>{errorMessage}</pre>
            </div>
          )}

          {successMessage && (
            <div className="custom-node-feedback custom-node-feedback-success">
              <strong>Sukses</strong>
              <p>{successMessage}</p>
            </div>
          )}

          {warnings.length > 0 && (
            <div className="custom-node-feedback custom-node-feedback-warning">
              <strong>Peringatan</strong>
              <ul>
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="modal-footer">
            <div className="button-group">
              <button type="button" className="cancel-button" onClick={onClose} disabled={isSubmitting}>
                Close
              </button>
              <button type="submit" className="save-button" disabled={isSubmitting}>
                {isSubmitting ? 'Uploading...' : 'Upload Custom Node'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CustomNodeUploadModal;
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

// Instead of importing the real api module (which pulls in axios,
// an ESM-only package that Jest can't parse), provide a manual mock
// so the module never gets loaded during these unit tests.
jest.mock('../services/api', () => {
  // create mocks inside the factory so we don't run into hoisting issues
  const uploadImage = jest.fn();
  const uploadJson = jest.fn();
  return {
    __esModule: true,
    default: {
      uploadImage,
      uploadJson,
    },
  };
});

import api from '../services/api';
import NodePropertiesModal from './NodePropertiesModal';

jest.mock('../services/api');

describe('NodePropertiesModal', () => {
  const baseProps = {
    availableNodes: [
      {
        id: 'input',
        name: 'Image Input',
        type: 'input',
        description: 'test',
        inputs: 0,
        outputs: 1,
        parameters: {},
      },
    ],
    onUploadingChange: jest.fn(),
  };

  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('does not render when closed', () => {
    const { container } = render(<NodePropertiesModal {...baseProps} isOpen={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows file input and "no file" message for empty input node', () => {
    render(
      <NodePropertiesModal
        {...baseProps}
        isOpen={true}
        node={{ id: 'n1', data: { nodeType: 'input', filename: '', file_id: null } }}
        onClose={jest.fn()}
        onUpdateNode={jest.fn()}
      />
    );

    expect(screen.getByText('Input File')).toBeInTheDocument();
    expect(screen.getByText('No file selected.')).toBeInTheDocument();

    // input[type=file] should exist
    // file input should be present in the modal
    const fileInput = document.querySelector('input[type=file]');
    expect(fileInput).toBeInTheDocument();
  });

  it('displays current filename and remove button when a file is present', () => {
    render(
      <NodePropertiesModal
        {...baseProps}
        isOpen={true}
        node={{ id: 'n1', data: { nodeType: 'input', filename: 'foo.png', file_id: 'abc' } }}
        onClose={jest.fn()}
        onUpdateNode={jest.fn()}
      />
    );

    expect(screen.getByText('Current file:')).toBeInTheDocument();
    expect(screen.getByText('foo.png')).toBeInTheDocument();
    expect(screen.getByText('Remove File')).toBeInTheDocument();
  });

  it('uploads an image and calls onUpdateNode', async () => {
    const mockUpdate = jest.fn();
    api.uploadImage.mockResolvedValue({ data: { file_id: '123', filename: 'bar.jpg' } });

    render(
      <NodePropertiesModal
        {...baseProps}
        isOpen={true}
        node={{ id: 'n1', data: { nodeType: 'input', filename: '', file_id: null } }}
        onClose={jest.fn()}
        onUpdateNode={mockUpdate}
      />
    );

    const fileInput = document.querySelector('input[type=file]');

    const file = new File(['dummy'], 'bar.jpg', { type: 'image/jpeg' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // wait for both the API call and the subsequent onUpdateNode invocation
    await waitFor(() => {
      expect(api.uploadImage).toHaveBeenCalledWith(file);
      expect(mockUpdate).toHaveBeenCalledWith('n1', {}, { file_id: '123', filename: 'bar.jpg' });
    });
  });

  it('clears existing file when remove button is clicked', () => {
    const mockUpdate = jest.fn();

    render(
      <NodePropertiesModal
        {...baseProps}
        isOpen={true}
        node={{ id: 'n1', data: { nodeType: 'input', filename: 'foo.png', file_id: 'abc' } }}
        onClose={jest.fn()}
        onUpdateNode={mockUpdate}
      />
    );

    fireEvent.click(screen.getByText('Remove File'));
    expect(mockUpdate).toHaveBeenCalledWith('n1', {}, { file_id: null, filename: '' });
  });
});

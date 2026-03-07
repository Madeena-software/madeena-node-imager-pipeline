import { render, screen } from '@testing-library/react';
import NodePalette from './NodePalette';

// We're not testing drag/drop behavior here, just that the pipeline category
// renders our TIFF JSON to DICOM node when it's provided in the node list.

describe('NodePalette', () => {
  const sampleNodes = [
    {
      id: 'wavelet_denoise',
      name: 'Wavelet Denoise',
      category: 'Pipeline',
      description: '',
      inputs: 1,
      outputs: 1,
      parameters: {},
    },
    {
      id: 'camera_calibration',
      name: 'Camera Calibration',
      category: 'Pipeline',
      description: '',
      inputs: 1,
      outputs: 1,
      parameters: {},
    },
    // artifact node with zero outputs should still be listed
    {
      id: 'tiff_json_to_dicom',
      name: 'TIFF JSON to DICOM',
      category: 'Pipeline',
      description: '',
      inputs: 1,
      outputs: 0,
      parameters: {},
    },
  ];

  it('shows nodes grouped by category and includes artifact processor', () => {
    render(<NodePalette nodes={sampleNodes} />);

    // category header should show parenthesis count (3)
    const header = screen.getByText('Pipeline').closest('.category-header');
    expect(header).toBeInTheDocument();
    expect(screen.getByText(/\(3\)/)).toBeInTheDocument();

    // expand the section so items are rendered
    if (header) {
      const { fireEvent } = require('@testing-library/react');
      fireEvent.click(header);
    }

    // verify that the TIFF JSON to DICOM item is rendered
    expect(screen.getByText('TIFF JSON to DICOM')).toBeInTheDocument();

    // artifact nodes should have the box icon
    expect(screen.getByText('📦')).toBeInTheDocument();
  });
});
